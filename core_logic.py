# core_logic.py

from api_services import call_deer_api_gpt
from config import DEFAULT_API_TIMEOUT_SHORT, DEFAULT_API_TIMEOUT_LONG, DEFAULT_DEER_MODEL
from utils import app_logger

def decompose_question_with_gpt(user_question):
    """
    使用GPT将用户问题分解为子问题。
    
    Args:
        user_question (str): 用户的原始问题
    
    Returns:
        list: 分解后的子问题列表
    """
    system_prompt = "你是一个帮助用户分解复杂问题的AI助手。请将用户问题分解为适合搜索引擎查询的子问题列表。"
    user_prompt_detail = (
        f"用户问题：\"{user_question}\"\n\n"
        "请将上述用户问题分解为3-5个具体的、独立的子问题或关键词短语。这些子问题应旨在收集全面的信息以回答原始问题。\n"
        "输出要求：\n"
        "- 以无序列表形式输出 (每行一个子问题，以'- '开头)。\n"
        "- 子问题应具有可搜索性，能直接作为搜索引擎的查询语句。\n"
        "- 确保子问题之间尽量不重复，并能覆盖原始问题的核心方面。"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_detail}
    ]
    
    app_logger.info(f"Decomposing question: {user_question}")
    raw_content = call_deer_api_gpt(messages, model=DEFAULT_DEER_MODEL, operation_timeout=DEFAULT_API_TIMEOUT_SHORT)
    
    if raw_content:
        sub_questions = [sq.strip().lstrip('- ').strip() for sq in raw_content.split('\n') if sq.strip().startswith('- ')]
        app_logger.info(f"Successfully decomposed into {len(sub_questions)} sub-questions")
        return [sq for sq in sub_questions if sq]
    else:
        app_logger.error("Failed to decompose question")
        print("错误: 未能从DeerAPI获取问题分解内容。")
        return []

def generate_report_with_gpt(original_question, search_data_map):
    """
    使用GPT将研究信息转化为一份面向CAD建模的技术规格清单。
    
    Args:
        original_question (str): 用户的原始问题
        search_data_map (dict): 搜索数据映射，键为子问题，值为搜索结果列表
    
    Returns:
        str: 生成的报告内容
    """
    system_prompt = (
        "你是一个AI助手，其核心任务是将用户的自然语言需求和相关的研究信息摘要，转化为一份结构化的、"
        "可直接用于指导CAD建模的技术规格清单。请专注于提取具体的几何特征、组件需求、材料规格和关键参数。"
        "你的输出必须是这份清单，避免不必要的叙述性文字。"
    )

    information_block = []
    for sub_q, snippets_list in search_data_map.items():
        if snippets_list and snippets_list != ["未能找到相关信息。"]:
            information_block.append(f"### 关于 \"{sub_q}\" 的研究摘要:\n")
            for i, snippet_info in enumerate(snippets_list):
                information_block.append(f"- {snippet_info}\n")
            information_block.append("\n")
    
    if not information_block:
        app_logger.warning("No search data available for report generation")
        return "未能从搜索中收集到足够的信息来生成技术规格清单。"
    
    compiled_search_data_string = "".join(information_block)

    user_prompt_detail = f"""原始用户需求: "{original_question}"

--- 已收集的相关研究信息摘要 ---
{compiled_search_data_string}
--- 研究信息摘要结束 ---

**任务：** 基于上述"原始用户需求"和"研究信息摘要"，请生成一份详细的 **"CAD建模技术规格清单"**。
这份清单应直接列出CAD设计师在建模时需要实现的具体条目。

**输出格式严格要求如下 (使用Markdown)：**

**CAD建模技术规格清单**

**1. 项目名称：** (根据原始用户需求生成一个简洁的项目名)

**2. CAD模型核心目标：** (用一句话描述需要通过CAD模型实现的核心功能或产品)

**3. 几何特征与结构要求 (Geometric Features & Structural Requirements):**
    * **外壳主体 (Main Enclosure Body):**
        * 大致形状: (例如：矩形箱体, 圆柱形, 特定流线型。如果信息不足，填写"根据整体布局确定 (TBD)")
        * 预估总体尺寸范围 (LxWxH): (例如: 约 200x150x100mm。如果信息不足，填写"TBD")
        * 壁厚建议: (例如: 3mm (ABS材料, 3D打印), 1.5mm (铝板)。如果信息不足，填写"TBD")
    * **通风口 (Ventilation Ports):**
        * 进气口类型/数量/大致位置: (例如: 底部格栅式进气口 x2, 前面板条形进气槽 x1。填写"TBD"如果无法确定)
        * 出气口类型/数量/大致位置: (例如: 顶部/后部风扇出风口 x1。填写"TBD"如果无法确定)
    * **组件安装点/接口 (Component Mounting Points/Interfaces):**
        * (例如: PCB固定柱 M3螺丝孔 x4, 电源模块安装板, LCD屏幕开孔 xx*yy mm, USB接口开孔。尽可能列出具体组件的安装需求)
    * **检修/操作接口 (Access/Operation Features):**
        * (例如: 可拆卸顶盖, 铰链式侧门, 电源按钮开孔, LED指示灯孔)
    * **内部结构 (Internal Structures):**
        * (例如: 用于引导气流的隔板, 线材固定槽/夹, 电池仓)
    * **其他结构特征:**
        * (例如: 底部防滑脚垫安装位, 提手)

**4. 关键组件清单与集成要求 (Key Components & Integration Requirements):**
    * (对于每个组件，列出类型、关键规格（如尺寸、型号）、数量，以及在CAD中需要考虑的集成方式)
    * - **散热风扇1:**
        * 类型: (例如: 轴流风扇, 涡轮风扇)
        * 尺寸: (例如: 80x80x25mm, 120mm直径。填写"TBD"如果无具体信息)
        * 数量:
        * 安装位置/朝向: (例如: 后板向上吹风)
    * - **散热风扇2 (如有):** (同上)
    * - **散热片/散热器 (Heatsink/Radiator):**
        * 类型: (例如: 挤压铝型材, CPU散热塔, 水冷排)
        * 预估尺寸/安装空间: (填写"TBD"如果无具体信息)
    * - **主控板 (Mainboard/PCB):**
        * 预估尺寸/安装孔位:
    * - **电源模块 (PSU):**
        * 类型/尺寸:
    * - *(根据研究信息继续列出其他需要集成的内部组件)*

**5. 材料选用规格 (Material Specifications):**
    * **主要外壳材料:** (例如: ABS塑料, PETG, 5052铝合金板)
        * 选用原因/特性: (简述，例如: 易于3D打印, 良好强度, 导热性好)
        * 厚度/规格: (例如: 3D打印壁厚3mm, 铝板厚度1.5mm)
    * **辅助材料 (如有):** (例如: 透明亚克力板 - 用于观察窗)

**6. 制造工艺提示 (Manufacturing Process Hints):**
    * 主要工艺: (例如: FDM 3D打印, SLA 3D打印,钣金加工, CNC加工)
    * CAD设计注意事项: (简述此工艺对CAD设计的特定要求，例如："FDM: 注意悬垂角度，避免过大支撑"；"钣金: 考虑最小折弯半径，展开图")

**7. 关键性能指标/约束 (Key Performance Indicators/Constraints - 若研究提及):**
    * (例如: 目标内部温度 < 50°C, 最大噪音 < 40dB, 整体重量 < 2kg)

**8. 待定参数/需进一步决策项 (TBD Parameters / Further Decisions Needed):**
    * (明确列出在此阶段无法确定，需要在后续详细设计中明确的关键参数或设计选择)

**请严格按照以上格式和要求生成清单。如果某些信息在研究摘要中确实无法找到或推断，请在该条目下明确注明"信息不足，TBD"或"需根据后续设计确定"。目标是最大化这份清单对CAD建模的直接可用性。**

开始生成"CAD建模技术规格清单"：
"""

    app_logger.info("Generating report with prompt length: %d characters", len(user_prompt_detail))
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_detail}
    ]
    
    report = call_deer_api_gpt(messages, model=DEFAULT_DEER_MODEL, operation_timeout=DEFAULT_API_TIMEOUT_LONG)
    
    if report:
        app_logger.info("Successfully generated report")
        return report
    else:
        app_logger.error("Failed to generate report")
        print("错误: 未能从DeerAPI获取报告内容。")
        return "无法生成技术规格清单，与DeerAPI通信时发生错误，或未获取到有效内容。"