import requests
import json
import os
from config import SERPER_API_KEY, DEFAULT_SERPER_RESULTS_NUM, DEER_API_KEY, DEER_API_BASE_URL
from api_services import search_serper, call_deer_api_gpt
from core_logic import decompose_question_with_gpt, generate_report_with_gpt
from utils import app_logger

# --- Configuration ---
# IMPORTANT: Replace with your actual API base URL from DeerAPI.
# This is an assumption based on your User-Agent.
DEER_API_BASE_URL = "https://api.deerapi.com/v1" 
                                                

# WARNING: The API key below was publicly shared.
# It is STRONGLY recommended to invalidate this key and use a new one,
# managing it securely via environment variables or a config file.
DEER_API_KEY = "sk-vQmif2Ott5QZxuvKa3h0rBG7gccoAwLzW0sYmwPD8UL05BXV" # Your provided API Key

SERPER_API_KEY = "95db38c6b511d9ea6f00ef87a0cfba7b91a3c22b" # Your Serper API Key

# --- Function Definitions ---

def call_deer_api_gpt(messages_payload, model="gpt-3.5-turbo", operation_timeout=60): # 默认超时增加到60秒
    """
    Helper function to call the DeerAPI GPT-like endpoint.
    'operation_timeout' 参数允许为不同操作设置不同的超时时间。
    """
    if not DEER_API_BASE_URL or "YOUR_DEER_API_BASE_URL" in DEER_API_BASE_URL:
        print("错误：请在脚本中正确设置 DEER_API_BASE_URL。")
        return None
    if not DEER_API_KEY or "YOUR_DEER_API_KEY" in DEER_API_KEY:
        print("错误：请设置有效的 DeerAPI 密钥 (DEER_API_KEY)。")
        return None

    api_url = f"{DEER_API_BASE_URL}/chat/completions"
    headers = {
        'Accept': 'application/json',
        'Authorization': DEER_API_KEY,
        'User-Agent': 'DeerAPI/1.0.0 (https://api.deerapi.com)',
        'Content-Type': 'application/json'
    }
    data = {
        "model": model,
        "messages": messages_payload
    }

    # print(f"DEBUG: Calling DeerAPI URL: {api_url} with timeout {operation_timeout}s") 
    # print(f"DEBUG: DeerAPI Payload: {json.dumps(data, indent=2, ensure_ascii=False)}")

    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=operation_timeout) 
        # print(f"DEBUG: DeerAPI Status Code: {response.status_code}")
        # print(f"DEBUG: DeerAPI Response Text: {response.text}")
        response.raise_for_status()
        
        response_json = response.json()
        content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content and response_json:
             if "error" in response_json:
                 print(f"DeerAPI Error in response: {response_json['error']}")
             elif not response_json.get("choices"):
                 print(f"DeerAPI Response missing 'choices': {response_json}")
        return content
    except requests.exceptions.Timeout:
        print(f"Error calling DeerAPI: Request timed out after {operation_timeout} seconds.") # 显示超时时长
        return None
    except requests.exceptions.HTTPError as http_err:
        print(f"Error calling DeerAPI: HTTP error occurred: {http_err}")
        if http_err.response is not None:
            try:
                print(f"DeerAPI Error Response Body: {http_err.response.json()}")
            except json.JSONDecodeError:
                print(f"DeerAPI Error Response Body (not JSON): {http_err.response.text}")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"Error calling DeerAPI: Request exception: {req_err}")
        return None
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"Error parsing DeerAPI response: {e}. Response was: {response.text if 'response' in locals() else 'No response object'}")
        return None

def decompose_question_with_gpt(user_question):
    # ... (messages payload remains the same) ...
    messages = [
        {"role": "system", "content": "你是一个帮助用户分解复杂问题的AI助手。请将用户问题分解为适合搜索引擎查询的子问题列表。"},
        {"role": "user", "content": f"用户问题：\"{user_question}\"\n\n请将上述用户问题分解为3-5个具体的子问题或关键词短语，这些子问题或短语适合用于搜索引擎查询，以收集相关信息来回答原始问题。请以列表形式输出这些子问题或短语，每个子问题占一行。"}
    ]
    # 使用较短的超时进行分解，例如30秒
    raw_content = call_deer_api_gpt(messages, operation_timeout=30) 
    
    if raw_content:
        sub_questions = [sq.strip().replace("- ", "").replace("* ", "") for sq in raw_content.split('\n') if sq.strip()]
        return [sq for sq in sub_questions if sq]
    else:
        print("Error: Failed to get content from DeerAPI for question decomposition.")
        return []

def generate_report_with_gpt(original_question, search_data):
    # ... (prompt_context generation remains the same) ...
    prompt_context = f"原始用户问题：\"{original_question}\"\n\n针对这个问题，我们进行了以下子问题的搜索，并获得了相关信息摘要：\n\n"
    # ... (rest of the prompt_context generation) ...
    has_search_data = False
    for sub_q, snippets_list in search_data.items():
        if snippets_list and snippets_list != ["未能找到相关信息。"]:
            has_search_data = True
            prompt_context += f"子问题： \"{sub_q}\"\n"
            for i, snippet_info in enumerate(snippets_list):
                prompt_context += f"  信息{i+1}：{snippet_info}\n"
            prompt_context += "\n"

    if not has_search_data:
        return "未能从搜索中收集到足够的信息来生成报告。"
    prompt_context += "请基于以上信息，围绕原始用户问题，生成一份综合性的建议报告。报告应清晰、有条理，并指出关键的设计考虑因素和可能的解决方案。如果信息来源明确，请适当引用其链接。\n报告内容："

    # 打印将要发送给报告生成API的文本长度，有助于调试
    print(f"  DEBUG: Length of prompt_context for report generation: {len(prompt_context)} characters")

    messages = [
        {"role": "system", "content": "你是一个专业的AI助手，擅长根据提供的信息生成综合报告。"},
        {"role": "user", "content": prompt_context}
    ]
    
    # 为报告生成使用更长的超时
    report = call_deer_api_gpt(messages, operation_timeout=120) 
    
    if report:
        return report
    else:
        print("Error: Failed to get content from DeerAPI for report generation.")
        return "无法生成报告，与DeerAPI通信时发生错误。"

def search_serper(query, api_key, num_results=5):
    """
    使用 Serper (google.serper.dev) API 执行搜索。
    """
    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": query,
        "num": num_results
    })
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    # print(f"  DEBUG: Sending to Serper: query='{query}', num_results={num_results}")
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        response.raise_for_status()
        search_results_json = response.json()
        organic_results = search_results_json.get('organic', [])
        return organic_results
    except requests.exceptions.Timeout:
        print(f"Error during Serper Search for '{query}': Request timed out.")
        return []
    except requests.exceptions.HTTPError as http_err:
        print(f"Error during Serper Search for '{query}': HTTP error occurred: {http_err}")
        if http_err.response is not None:
            try:
                print(f"Serper API Error Response: {http_err.response.json()}")
            except json.JSONDecodeError:
                print(f"Serper API Error Response (not JSON): {http_err.response.text}")
        return []
    except requests.exceptions.RequestException as req_err:
        print(f"Error during Serper Search for '{query}': Request exception: {req_err}")
        return []
    except json.JSONDecodeError:
        print(f"Failed to decode JSON response from Serper for '{query}'. Response was: {response.text if 'response' in locals() else 'No response object'}")
        return []

def run_assistant():
    # 检查API密钥和URL是否已配置
    if not SERPER_API_KEY or len(SERPER_API_KEY) < 20:
        print("错误：请在config.py中设置有效的Serper API密钥。")
        return
    if not DEER_API_KEY or DEER_API_KEY.startswith("sk-YOUR_DEER_API_KEY"):
        print("错误：请在config.py中设置有效的DeerAPI密钥。")
        return
    if not DEER_API_BASE_URL or "YOUR_DEER_API_BASE_URL" in DEER_API_BASE_URL:
        print("错误：请在config.py中设置有效的DeerAPI基础URL。")
        return

    user_natural_question = input("请输入您的自然语言提问：")
    if not user_natural_question.strip():
        print("输入不能为空，请重新运行并提问。")
        return

    print("\n[1/4] 正在理解并分解您的问题 (使用DeerAPI)...")
    app_logger.info(f"Starting decomposition for: {user_natural_question}")
    sub_questions = decompose_question_with_gpt(user_natural_question)

    if not sub_questions:
        print("抱歉，无法分解您的问题。请尝试更清晰地描述或检查DeerAPI连接。")
        app_logger.warning(f"Failed to decompose question: {user_natural_question}")
        return
    else:
        print(f"\n已将您的问题分解为以下子问题：")
        for i, sq in enumerate(sub_questions):
            print(f"  {i+1}. {sq}")
        app_logger.info(f"Decomposed into sub_questions: {sub_questions}")

    all_search_snippets_for_report = {}
    print("\n[2/4] 正在为每个子问题执行搜索 (使用Serper API)...")
    for i, sub_q in enumerate(sub_questions):
        app_logger.info(f"Searching for sub_question: {sub_q}")
        print(f"  正在搜索子问题 {i+1}/{len(sub_questions)}: \"{sub_q}\"")
        results = search_serper(sub_q, SERPER_API_KEY, num_results=DEFAULT_SERPER_RESULTS_NUM)
        
        current_sub_q_snippets = []
        if results:
            print(f"    找到 {len(results)} 条结果 for '{sub_q}'")
            for result_item in results:
                title = result_item.get('title', '无标题')
                link = result_item.get('link', '#')
                snippet_text = result_item.get('snippet', '无摘要').replace('\n', ' ')
                current_sub_q_snippets.append(f"标题: {title}, 链接: {link}, 摘要: {snippet_text}")
        else:
            print(f"    未能找到 '{sub_q}' 的相关结果。")
            current_sub_q_snippets.append("未能找到相关信息。")
        
        all_search_snippets_for_report[sub_q] = current_sub_q_snippets
        print(f"    完成搜索: \"{sub_q}\"")

    print("\n[3/4] 正在整合信息并生成报告 (使用DeerAPI)...")
    app_logger.info("Starting report generation.")
    final_report = generate_report_with_gpt(user_natural_question, all_search_snippets_for_report)

    print("\n[4/4] 综合报告生成完毕：")
    print("=" * 30 + " 报告开始 " + "=" * 30)
    print(final_report)
    print("=" * 30 + " 报告结束 " + "=" * 30)
    app_logger.info("Report generation complete.")

if __name__ == '__main__':
    run_assistant()