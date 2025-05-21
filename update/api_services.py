import requests
import json
from config1 import API_KEY, DEFAULT_DEER_MODEL
from utils import app_logger

def call_deer_api_gpt(messages_payload, model=DEFAULT_DEER_MODEL, operation_timeout=60):
    """
    Calls the DeerAPI GPT-like endpoint.
    """
    deer_api_base_url = API_KEY.get("DEER_API_BASE_URL")
    deer_api_key = API_KEY.get("DEER_API_KEY")

    if not deer_api_base_url or "YOUR_DEER_API_BASE_URL" in deer_api_base_url:
        app_logger.error("DEER_API_BASE_URL not properly configured in config1.py")
        print("错误：请在config1.py中正确设置 DEER_API_BASE_URL。")
        return None
    if not deer_api_key or deer_api_key.startswith("sk-YOUR_DEER_API_KEY") or len(deer_api_key) < 20:
        app_logger.error("DEER_API_KEY not properly configured in config1.py")
        print("错误：请在config1.py中设置有效的 DeerAPI 密钥 (DEER_API_KEY)。")
        return None

    api_url = f"{deer_api_base_url}/chat/completions"
    headers = {
        'Accept': 'application/json',
        'Authorization': deer_api_key,
        'User-Agent': 'DeerAPIClient/1.0.0 (PythonApp)',
        'Content-Type': 'application/json'
    }
    data = {
        "model": model,
        "messages": messages_payload
    }

    app_logger.debug(f"Calling DeerAPI: URL={api_url}, Model={model}, Timeout={operation_timeout}s")

    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=operation_timeout)
        response.raise_for_status() 
        response_json = response.json()
        
        choices = response_json.get("choices")
        if choices and isinstance(choices, list) and len(choices) > 0:
            message = choices[0].get("message")
            if message and isinstance(message, dict):
                content = message.get("content")
                if content: 
                    app_logger.debug(f"DeerAPI successful response. Content length: {len(content)}")
                    return content
                else:
                    app_logger.error(f"DeerAPI: 'content' is missing or empty in message. Response: {response_json}")
                    print("DeerAPI 错误: 响应消息中缺少 'content' 或内容为空。")
            else:
                app_logger.error(f"DeerAPI: 'message' is missing or not a dict in choices[0]. Response: {response_json}")
                print("DeerAPI 错误: 响应中 'message' 结构无效。")
        elif "error" in response_json: 
            app_logger.error(f"DeerAPI returned an error: {response_json['error']}")
            print(f"DeerAPI 错误: {response_json['error']}")
        else: 
            app_logger.error(f"DeerAPI: 'choices' array is missing, empty, or invalid. Response: {response_json}")
            print("DeerAPI 错误: 响应中 'choices' 结构无效或缺失。")
        return None

    except requests.exceptions.Timeout:
        app_logger.error(f"DeerAPI request timed out after {operation_timeout} seconds for URL: {api_url}")
        print(f"调用DeerAPI错误: 请求在 {operation_timeout} 秒后超时。")
        return None
    except requests.exceptions.HTTPError as http_err:
        app_logger.error(f"DeerAPI HTTP error: {http_err}. Response: {http_err.response.text if http_err.response else 'No response body'}")
        print(f"调用DeerAPI错误: HTTP错误: {http_err}")
        if http_err.response is not None:
            try:
                error_body = http_err.response.json()
                app_logger.error(f"DeerAPI Error Response Body (JSON): {error_body}")
                print(f"DeerAPI 错误响应体: {error_body}")
            except json.JSONDecodeError:
                error_text = http_err.response.text
                app_logger.error(f"DeerAPI Error Response Body (text): {error_text}")
                print(f"DeerAPI 错误响应体 (非JSON): {error_text}")
        return None
    except requests.exceptions.RequestException as req_err:
        app_logger.error(f"DeerAPI request exception: {req_err}")
        print(f"调用DeerAPI错误: 请求异常: {req_err}")
        return None
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        response_text_for_log = 'No response object or text available'
        if 'response' in locals() and hasattr(response, 'text'):
            response_text_for_log = response.text
        app_logger.error(f"Error parsing DeerAPI response: {e}. Response: {response_text_for_log}")
        print(f"解析DeerAPI响应错误: {e}。")
        return None

# The 'num_results' parameter is now mandatory and will be supplied by main.py
def search_serper(query, num_results):
    """
    Uses Serper (google.serper.dev) API to perform a search.
    'num_results' is passed by the caller (e.g., main.py).
    """
    serper_api_key = API_KEY.get("SERPER_API_KEY")
    serper_search_url = API_KEY.get("SERPER_SEARCH_URL")

    if not serper_api_key or len(serper_api_key) < 20:
        app_logger.error("SERPER_API_KEY not properly configured in config1.py")
        print("错误：请在config1.py中正确设置 SERPER_API_KEY。")
        return [] 
    if not serper_search_url:
        app_logger.error("SERPER_SEARCH_URL not properly configured in config1.py")
        print("错误：请在config1.py中正确设置 SERPER_SEARCH_URL。")
        return []

    payload = json.dumps({"q": query, "num": num_results})
    headers = {'X-API-KEY': serper_api_key, 'Content-Type': 'application/json'}
    
    app_logger.debug(f"Sending to Serper: URL='{serper_search_url}', Query='{query}', Num_results={num_results}")

    try:
        response = requests.post(serper_search_url, headers=headers, data=payload, timeout=10)
        response.raise_for_status()
        search_results_json = response.json()
        organic_results = search_results_json.get('organic', [])
        app_logger.debug(f"Serper search for '{query}' returned {len(organic_results)} results.")
        return organic_results
    except requests.exceptions.Timeout:
        app_logger.error(f"Serper search timed out for query: {query}")
        print(f"Serper搜索 '{query}' 超时。")
        return []
    except requests.exceptions.HTTPError as http_err:
        app_logger.error(f"Serper HTTP error for query '{query}': {http_err}. Response: {http_err.response.text if http_err.response else 'No response body'}")
        print(f"Serper搜索 '{query}' 时发生HTTP错误: {http_err}")
        if http_err.response is not None:
            try:
                error_body = http_err.response.json()
                app_logger.error(f"Serper API Error Response (JSON): {error_body}")
                print(f"Serper API 错误响应: {error_body}")
            except json.JSONDecodeError:
                error_text = http_err.response.text
                app_logger.error(f"Serper API Error Response (text): {error_text}")
                print(f"Serper API 错误响应 (非JSON): {error_text}")
        return []
    except requests.exceptions.RequestException as req_err:
        app_logger.error(f"Serper request exception for query '{query}': {req_err}")
        print(f"Serper搜索 '{query}' 时发生请求异常: {req_err}")
        return []
    except json.JSONDecodeError:
        response_text_for_log = 'No response object or text available'
        if 'response' in locals() and hasattr(response, 'text'):
            response_text_for_log = response.text
        app_logger.error(f"Failed to decode JSON response from Serper for '{query}'. Response: {response_text_for_log}")
        print(f"未能解码来自Serper的JSON响应 '{query}'。")
        return []
