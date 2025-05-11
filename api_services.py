import requests
import json
from config import DEER_API_KEY, DEER_API_BASE_URL, DEFAULT_DEER_MODEL
from utils import app_logger

def call_deer_api_gpt(messages_payload, model=DEFAULT_DEER_MODEL, operation_timeout=60):
    """
    调用DeerAPI GPT-like端点。
    
    Args:
        messages_payload (list): 消息列表
        model (str): 使用的模型名称
        operation_timeout (int): 操作超时时间（秒）
    
    Returns:
        str: API响应的内容，如果发生错误则返回None
    """
    if not DEER_API_BASE_URL or "YOUR_DEER_API_BASE_URL" in DEER_API_BASE_URL:
        app_logger.error("DEER_API_BASE_URL not properly configured")
        print("错误：请在config.py中正确设置 DEER_API_BASE_URL。")
        return None
    if not DEER_API_KEY or DEER_API_KEY.startswith("sk-YOUR_DEER_API_KEY"):
        app_logger.error("DEER_API_KEY not properly configured")
        print("错误：请在config.py中设置有效的 DeerAPI 密钥 (DEER_API_KEY)。")
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

    app_logger.debug(f"Calling DeerAPI: {api_url} with model {model}, timeout {operation_timeout}s")

    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=operation_timeout)
        response.raise_for_status()
        response_json = response.json()
        content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content and response_json:
             if "error" in response_json:
                 app_logger.error(f"DeerAPI Error in response: {response_json['error']}")
                 print(f"DeerAPI Error in response: {response_json['error']}")
             elif not response_json.get("choices"):
                 app_logger.error(f"DeerAPI Response missing 'choices': {response_json}")
                 print(f"DeerAPI Response missing 'choices': {response_json}")
        return content
    except requests.exceptions.Timeout:
        app_logger.error(f"DeerAPI request timed out after {operation_timeout} seconds")
        print(f"Error calling DeerAPI: Request timed out after {operation_timeout} seconds.")
        return None
    except requests.exceptions.HTTPError as http_err:
        app_logger.error(f"DeerAPI HTTP error: {http_err}")
        print(f"Error calling DeerAPI: HTTP error occurred: {http_err}")
        if http_err.response is not None:
            try:
                error_body = http_err.response.json()
                app_logger.error(f"DeerAPI Error Response Body: {error_body}")
                print(f"DeerAPI Error Response Body: {error_body}")
            except json.JSONDecodeError:
                error_text = http_err.response.text
                app_logger.error(f"DeerAPI Error Response Body (not JSON): {error_text}")
                print(f"DeerAPI Error Response Body (not JSON): {error_text}")
        return None
    except requests.exceptions.RequestException as req_err:
        app_logger.error(f"DeerAPI request exception: {req_err}")
        print(f"Error calling DeerAPI: Request exception: {req_err}")
        return None
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        response_text = response.text if 'response' in locals() and hasattr(response, 'text') else 'No response text available'
        app_logger.error(f"Error parsing DeerAPI response: {e}. Response was: {response_text}")
        print(f"Error parsing DeerAPI response: {e}. Response was: {response_text}")
        return None

def search_serper(query, api_key, num_results=5):
    """
    使用 Serper (google.serper.dev) API 执行搜索。
    
    Args:
        query (str): 搜索查询
        api_key (str): Serper API密钥
        num_results (int): 返回结果数量
    
    Returns:
        list: 搜索结果列表，如果发生错误则返回空列表
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
    app_logger.debug(f"Sending to Serper: query='{query}', num_results={num_results}")
    
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        response.raise_for_status()
        search_results_json = response.json()
        organic_results = search_results_json.get('organic', [])
        return organic_results
    except requests.exceptions.Timeout:
        app_logger.error(f"Serper search timed out for query: {query}")
        print(f"Error during Serper Search for '{query}': Request timed out.")
        return []
    except requests.exceptions.HTTPError as http_err:
        app_logger.error(f"Serper HTTP error for query '{query}': {http_err}")
        print(f"Error during Serper Search for '{query}': HTTP error occurred: {http_err}")
        if http_err.response is not None:
            try:
                error_body = http_err.response.json()
                app_logger.error(f"Serper API Error Response: {error_body}")
                print(f"Serper API Error Response: {error_body}")
            except json.JSONDecodeError:
                error_text = http_err.response.text
                app_logger.error(f"Serper API Error Response (not JSON): {error_text}")
                print(f"Serper API Error Response (not JSON): {error_text}")
        return []
    except requests.exceptions.RequestException as req_err:
        app_logger.error(f"Serper request exception for query '{query}': {req_err}")
        print(f"Error during Serper Search for '{query}': Request exception: {req_err}")
        return []
    except json.JSONDecodeError:
        response_text = response.text if 'response' in locals() and hasattr(response, 'text') else 'No response text available'
        app_logger.error(f"Failed to decode JSON response from Serper for '{query}'. Response was: {response_text}")
        print(f"Failed to decode JSON response from Serper for '{query}'. Response was: {response_text}")
        return [] 