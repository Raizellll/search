# SmartCADReportGenerator/core_logic.py

import json # For parsing structured output from LLM
from api_services import call_deer_api_gpt
from config1 import ( # Assuming config1.py is correctly set up
    DEFAULT_API_TIMEOUT_SHORT,
    DEFAULT_API_TIMEOUT_MEDIUM,
    DEFAULT_API_TIMEOUT_LONG,
    DEFAULT_DEER_MODEL
)
from utils import app_logger

def decompose_question_with_gpt(user_question, stage="stage1"):
    """
    Decomposes the user's question into search queries.
    The prompt aims for specific, actionable queries suitable for finding detailed solutions.
    """
    # This system prompt encourages queries that find visual/structural details
    system_prompt = (
        "You are an AI research assistant. Your goal is to help a user find detailed, existing solutions or modification examples "
        "for their project by formulating effective search queries. These queries should aim to find resources that provide "
        "visual information (images, diagrams, 3D model views), structural details, material choices, and step-by-step guides."
    )
    user_prompt_detail = (
        f"User's project request: \"{user_question}\"\n\n"
        "Please generate 3-5 distinct search queries to find existing, well-documented solutions or modifications relevant to this request. "
        "Prioritize queries that would likely lead to pages with visual examples (e.g., project showcases, Thingiverse pages, Instructables, YouTube tutorials with clear visuals), "
        "detailed build logs, or specific design files.\n"
        "Output requirements:\n"
        "- Each search query on a new line.\n"
        "- Each query must start with '- '.\n"
        "- Queries should be specific enough to find actionable examples."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_detail}
    ]
    
    app_logger.info(f"Decomposing question ({stage}) for: \"{user_question}\"")
    raw_content = call_deer_api_gpt(messages, model=DEFAULT_DEER_MODEL, operation_timeout=DEFAULT_API_TIMEOUT_SHORT)
    
    if raw_content:
        # Process lines, remove '- ' prefix, and filter out empty strings
        sub_questions = [
            sq.strip().lstrip('- ').strip() 
            for sq in raw_content.splitlines() # Use splitlines() for better handling of various newline chars
            if sq.strip().startswith('- ')
        ]
        # Further filter to ensure no empty strings remain after stripping
        sub_questions = [sq for sq in sub_questions if sq]

        if sub_questions:
            app_logger.info(f"Successfully decomposed ({stage}) into {len(sub_questions)} search queries: {sub_questions}")
            return sub_questions
        else:
            app_logger.warning(f"Decomposition ({stage}) for \"{user_question}\" yielded no valid search queries from raw content: \"{raw_content}\"")
            print(f"错误 ({stage}): 问题分解未能生成有效的搜索查询。AI返回内容可能不符合预期格式。")
            return []
    else:
        app_logger.error(f"Failed to get raw content for question decomposition ({stage}): \"{user_question}\"")
        print(f"错误 ({stage}): 未能从AI获取问题分解内容。")
        return []

def generate_preliminary_summary_and_questions(original_question, search_data_map_stage1):
    """
    Generates a preliminary summary of research and clarifying questions for the user.
    Outputs a tuple: (summary_string, questions_list_of_dicts)
    """
    system_prompt = (
        "You are an AI research analyst. Based on an initial set of search results for a user's project request, "
        "your task is to: \n"
        "1. Provide a very brief (2-3 sentences) summary of the key themes or types of solutions found so far.\n"
        "2. Identify 2-4 critical ambiguities, decision points, or missing pieces of information that, if clarified by the user, "
        "would significantly help in creating a detailed and specific design specification later.\n"
        "3. Formulate these as clear, concise, and actionable questions for the user.\n"
        "Your entire output MUST be a valid JSON object with two top-level keys: 'summary' (a string) and 'questions' "
        "(a list of question objects). Each question object MUST have an 'id' (string, e.g., 'q1_material') and a 'text' (string, the question itself)."
        "Do NOT include any text or explanations outside of this single JSON object. Ensure the JSON is well-formed."
    )

    information_block = []
    has_valid_search_data = False
    if search_data_map_stage1: # Check if the map itself is not None
        for sub_q, snippets_list in search_data_map_stage1.items():
            # Ensure snippets_list is iterable and filter out None or placeholder "未能找到相关信息。"
            valid_snippets = [s for s in snippets_list if s and s != "未能找到相关信息。"]
            if valid_snippets:
                has_valid_search_data = True
                information_block.append(f"### Findings for query: \"{sub_q}\"\n")
                for snippet_info in valid_snippets:
                    information_block.append(f"- {snippet_info}\n")
                information_block.append("\n")
    
    compiled_search_data_string_stage1 = "".join(information_block)
    if not has_valid_search_data:
        compiled_search_data_string_stage1 = "No specific information was found in the initial search. Please formulate general clarifying questions based on the original request and common design considerations for such projects."

    user_prompt_detail = f"""Original User Request: "{original_question}"

--- Initial Research Findings (Context) ---
{compiled_search_data_string_stage1}
--- End of Initial Research Findings ---

Based on the Original User Request and the Initial Research Findings, please provide your analysis.

**Strict Output Format (Valid JSON Object Only - no extra text, no markdown backticks around the JSON itself in your final response):**
{{
  "summary": "Your concise summary of initial findings here (2-3 sentences maximum). If no specific findings, state that and suggest general areas to clarify.",
  "questions": [
    {{
      "id": "q1_material_preference",
      "text": "What primary material are you considering for this project (e.g., 3D Printed PLA/PETG, Carbon Fiber, Aluminum, Wood, etc.)?"
    }},
    {{
      "id": "q2_key_component_model",
      "text": "Is there a specific model for the main component this project revolves around (e.g., a particular GPS module model like 'Beitian BN-220', a specific sensor, a type of motor)? If so, please provide the model name/number."
    }},
    {{
      "id": "q3_critical_dimension_or_constraint",
      "text": "Are there any critical dimensions, existing mounting points to interface with, or specific constraints from the target environment (e.g., maximum allowable size for a bracket, a specific screw hole pattern on a drone frame, weight limit) that absolutely must be considered?"
    }},
    {{
      "id": "q4_desired_feature_or_style",
      "text": "Beyond the core function, are there any specific secondary features, functionalities, or overall aesthetic styles you definitely want to include or avoid (e.g., 'must be easily detachable using thumbscrews', 'prefer a rugged, industrial design', 'needs to be waterproof', 'avoid any sharp external edges')?"
    }}
  ]
}}
""" # Removed the ```json ``` backticks from the example in the prompt to avoid confusion for the LLM.
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_detail}
    ]

    app_logger.info(f"Generating preliminary summary and questions for: \"{original_question}\"")
    raw_response = call_deer_api_gpt(messages, model=DEFAULT_DEER_MODEL, operation_timeout=DEFAULT_API_TIMEOUT_MEDIUM)

    # Define fallback values
    fallback_summary = f"抱歉，未能为您的请求 '{original_question}' 生成初步总结。AI的响应可能不符合预期格式或发生了API错误。"
    fallback_questions = [
        {"id": "fallback_q1_material", "text": "您期望使用什么主要材料？"},
        {"id": "fallback_q2_component", "text": "您项目中是否有关键的组件型号需要考虑？"},
        {"id": "fallback_q3_constraints", "text": "是否有必须遵守的关键尺寸或约束条件？"}
    ]

    if raw_response:
        try:
            # LLMs might sometimes wrap their JSON in markdown, try to strip it.
            cleaned_response = raw_response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[len("```json"):]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-len("```")]
            cleaned_response = cleaned_response.strip() # Strip again after removing potential markdown

            parsed_output = json.loads(cleaned_response)
            
            # Validate the structure of the parsed output
            if isinstance(parsed_output, dict) and \
               "summary" in parsed_output and isinstance(parsed_output["summary"], str) and \
               "questions" in parsed_output and isinstance(parsed_output["questions"], list):
                
                # Further validate each question object in the list
                questions_valid = True
                if not parsed_output["questions"]: # An empty list of questions is acceptable
                    app_logger.info("AI returned an empty list for clarifying questions, which is acceptable.")
                else:
                    for q_item in parsed_output["questions"]:
                        if not (isinstance(q_item, dict) and "id" in q_item and isinstance(q_item["id"], str) \
                                and "text" in q_item and isinstance(q_item["text"], str)):
                            questions_valid = False
                            app_logger.error(f"Invalid question item format: {q_item}")
                            break
                
                if questions_valid:
                    app_logger.info("Successfully parsed preliminary summary and questions from AI.")
                    return parsed_output["summary"], parsed_output["questions"]
                else:
                    app_logger.error(f"Parsed JSON 'questions' list contains items not in the expected format. Parsed questions: {parsed_output['questions']}")
            else:
                app_logger.error(f"Parsed JSON from AI for summary/questions is not in the expected top-level format (missing 'summary' or 'questions' keys, or incorrect types). Parsed: {parsed_output}")
        
        except json.JSONDecodeError as e:
            app_logger.error(f"Failed to parse JSON response for summary/questions: {e}. Raw response snippet: {raw_response[:500]}")
        except Exception as e: # Catch any other unexpected error during parsing
            app_logger.error(f"An unexpected error occurred during parsing of summary/questions: {e}. Raw response snippet: {raw_response[:500]}")

        app_logger.warning("Falling back to default summary/questions due to parsing, format, or API error.")
        return fallback_summary, fallback_questions
        
    else:
        app_logger.error(f"Failed to get any response from AI for preliminary summary and questions for: \"{original_question}\"")
        return fallback_summary, fallback_questions


def generate_report_with_gpt(original_question, search_data_map, augmented_user_input_details=""):
    """
    Generates a detailed Text-to-CAD Design Specification, prioritizing and attempting to
    reproduce specific visual and structural details found in the research context and user feedback.
    """
    system_prompt = (
        "You are an expert AI CAD Design Assistant. Your primary task is to synthesize research findings and specific user requirements into a detailed "
        "textual specification for a physical product. This specification is intended to be as close as possible to a "
        "direct input for a text-to-CAD generation system. \n"
        "CRITICAL INSTRUCTION: You MUST meticulously review the 'Research Context' and any 'Specific User Requirements' provided. If this context contains specific "
        "descriptions of shapes, colors, materials, dimensions, assembly methods, or visual examples (even if described textually), "
        "your primary goal is to **incorporate and reproduce these specific details** into the relevant sections of the output format. "
        "Prioritize concrete details from the research and user inputs over generic suggestions. If multiple conflicting specific details are found for the same feature, "
        "choose the one that appears most relevant or well-documented, or note the alternatives if highly distinct and significant. "
        "If research/user input lacks a specific detail for a required field, then and only then should you make a sensible, common-knowledge-based design choice or state '[User to Specify/Verify Dimension]' or '[Standard Dimensions Apply for this type of component]'. "
        "Adhere strictly to the output format."
    )
    
    information_block = []
    has_valid_search_data = False
    if search_data_map: # Ensure search_data_map is not None
        for sub_q, snippets_list in search_data_map.items():
            valid_snippets = [s for s in snippets_list if s and s != "未能找到相关信息。"]
            if valid_snippets:
                has_valid_search_data = True
                information_block.append(f"### Research Findings for Query: \"{sub_q}\"\n")
                for i, snippet_info in enumerate(valid_snippets):
                    information_block.append(f"- {snippet_info}\n")
                information_block.append("\n")
    
    # Check if there's any meaningful input to proceed with
    if not has_valid_search_data and not (augmented_user_input_details and augmented_user_input_details.strip()):
        app_logger.warning(f"No valid search data and no specific user inputs for CAD specification for original request: \"{original_question}\"")
        return "未能收集到足够的信息（包括有效的搜索结果和用户具体要求）来生成详细的CAD设计规格。"

    compiled_search_data_string = "".join(information_block)
    if not compiled_search_data_string.strip(): # If block is empty after processing
        compiled_search_data_string = "No specific information was found in the detailed search. Relying primarily on user requirements and general design knowledge for common components of this type."

    user_requirements_section = ""
    if augmented_user_input_details and augmented_user_input_details.strip():
        user_requirements_section = f"""--- Specific User Requirements (Based on Clarifications) ---
{augmented_user_input_details}
--- End of Specific User Requirements ---

"""

    # The detailed Text-to-CAD template from the previous turn
    user_prompt_detail = f"""Original User Request: "{original_question}"

{user_requirements_section}
--- Summary of Detailed Information Found Online (Research Context for Stage 2) ---
{compiled_search_data_string}
--- End of Online Information Summary ---

**TASK:**
Based *primarily and meticulously* on the "Specific User Requirements" (if provided) and then on the specific details found in the "Research Context", generate a detailed **Text-to-CAD Design Specification**.
If the research or user requirements provide specific shapes, colors, materials, dimensions, or assembly methods, **you must prioritize using and describing these specific details**.
If information is lacking for a particular required field, make a sensible, common design choice and clearly indicate this (e.g., by stating "Based on common practice for [item type]..." or "Assuming standard dimensions for [component]...").
Your response MUST strictly follow the structure, headings, and level of detail exemplified below. Ensure all numbered sections and their sub-points are addressed.

**OUTPUT FORMAT (Strictly Adhere):**

**Project Name:** (Infer a suitable project name, e.g., "Custom Lightweight GPS Mount for [Drone Model/GPS Model if specified by user]")

**1. Base Component & Overall Design Intent:**
    * **Target Device:** (Specify based on user input or research, e.g., "Beitian BN-220 GPS Module")
    * **Enclosure/Mount Type:** (Describe based on user input or research, e.g., "Minimalist carbon fiber bracket")
    * **Primary Objective:** (e.g., "Securely mount the specified GPS module to a UAV, fabricated from carbon fiber, attached via M3 screws, prioritizing lightweight design.")

**2. Materials & Construction:**
    * **Primary Material (Prioritize user choice, then research):** (e.g., "Carbon Fiber Sheet, as specified by user.")
    * **Wall Thickness/Material Gauge (From user input, research, or best practice):** (e.g., "User specified 1.5mm thickness," or "1.5mm, a common choice for lightweight carbon fiber UAV parts found in research.")
    * **Recommended Color (From user input, research, or functional suggestion):** (e.g., "Matte Black, as specified by user for low visibility.")

**3. Detailed Geometry and Form (Prioritize user input and specific research details):**
    * **Overall Form Factor Description:** (Describe the general 3D shape. E.g., "A compact, low-profile mounting plate conforming to user's desire for minimalism, with integrated supports for the Beitian BN-220 GPS module. The plate will feature M3 mounting holes as per user specification.")
    * **Key Geometric Features:**
        * (e.g., "GPS Module Housing: A recessed rectangular area of 22.5mm x 20.5mm with 7mm depth to snugly fit the Beitian BN-220 module. Internal corners filleted at 1mm radius.")
        * (e.g., "Mounting Interface to UAV: Base flange section (e.g., 40mm x [UserSpecifiedWidth]mm x 1.5mm thick) with two 3.2mm diameter through-holes for M3 screws, spaced [UserSpecifiedHoleSpacing]mm apart, countersunk on the top surface, as per user's attachment requirement.")
    * **Edge Treatments:** (e.g., "All external edges to be lightly chamfered (0.5mm x 45 deg) for handling and to match finish of typical carbon fiber parts.")
    * **Lightweighting Features:** (e.g., "Hexagonal cutouts (8mm across flats) on non-load-bearing areas of the base flange, if user desires maximum weight reduction and research supports this for carbon fiber.")
    * **Surface Finish Suggestion:** (e.g., "Standard matte or semi-gloss finish typical of cut carbon fiber sheet.")

**4. Component Dimensions:**
    * **GPS Module Dimensions (User-specified or from research):** (e.g., "Beitian BN-220: 22mm x 20mm x 6.5mm, as specified by user.")
    * **Overall Bracket/Enclosure Approximate Dimensions (L x W x H):** (Derive, e.g., "Approximately 40mm x [UserSpecifiedWidthBasedOnHoleSpacing]mm x 20mm (including GPS module height).")

**5. Active/Passive Cooling:** (Typically N/A for GPS mount, confirm based on context. If not applicable, state 'N/A - Not required for this component type based on research and common usage.')
**6. Ventilation:** (Typically N/A for open GPS bracket, confirm based on context. If not applicable, state 'N/A - Open bracket design, dedicated ventilation not required.')

**7. Port Access Cutouts (Specific to GPS Module):**
    * (e.g., "One rectangular cutout (5mm x 3mm) positioned to allow access for the Beitian BN-220's standard JST-SH 4-pin connector.")

**8. Mounting to UAV (Based on user input):**
    * **Method:** (e.g., "Direct screw mount to UAV frame using existing M3 screw holes.")
    * **Fasteners:** (e.g., "Requires two M3x[UserToSpecifyLengthBasedOnFrame]mm screws.")

**9. Assembly:** (Typically single piece for simple bracket. If not, describe assembly steps if research provides any.)
**10. Cable Management:**
    * (e.g., "Two small integrated loops (1.5mm wide, 4mm long slots) on the underside for zip-tying the BN-220 cable, as per user's desire for clean installation.")

**11. Additional Design Considerations & Constraints (User-specified or critical research findings):**
    * (e.g., "User requires GPS antenna patch to have clear skyward orientation. The design ensures this." or "The carbon fiber material chosen by user offers excellent EMI shielding but ensure antenna is not directly underneath.")

Please generate the detailed Text-to-CAD Design Specification now. Ensure all sections above are addressed comprehensively, making logical inferences from the research context and **giving highest priority to the Specific User Requirements**. If a section like 'Active/Passive Cooling' is not applicable, explicitly state 'N/A' or 'Not applicable for this design' and briefly explain why if helpful.
"""

    app_logger.info(f"Generating final Text-to-CAD specification for \"{original_question}\" (augmented with user feedback & detailed research). Prompt length: {len(user_prompt_detail)} characters.")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_detail}
    ]
    
    report = call_deer_api_gpt(messages, model=DEFAULT_DEER_MODEL, operation_timeout=DEFAULT_API_TIMEOUT_LONG)
    
    if report:
        app_logger.info(f"Successfully generated final Text-to-CAD specification for \"{original_question}\".")
        return report
    else:
        app_logger.error(f"Failed to generate final Text-to-CAD specification for \"{original_question}\".")
        print("错误: 未能从AI获取最终的Text-to-CAD设计规格内容。")
        return "无法生成最终的Text-to-CAD设计规格，与AI通信时发生错误，或未获取到有效内容。"
