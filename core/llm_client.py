import os
import json
import re
import yaml
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(dotenv_path="config/secrets.env")

class DeepSeekClient:
    def __init__(self):
        # 读取配置
        with open("config/config.yaml", "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("❌ 未找到 DEEPSEEK_API_KEY")
            
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.config["llm"]["base_url"]
        )
        self.model = self.config["llm"]["model_name"]
        print(f"🧠 大脑核心已切换: {self.model}")

    def _clean_think_tag(self, text):
        """
        清洗 DeepSeek-R1 的 <think> 标签
        R1 会先输出 <think>...</think>，这会导致 json 解析失败
        我们只取 </think> 之后的内容
        """
        if "<think>" in text:
            # 使用正则去掉 <think>...</think> 之间的所有内容 (包括换行)
            text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        
        # 有时候模型会在 json 外面套 markdown，比如 ```json ... ```
        # 这一步通用的清洗
        if "```" in text:
            text = text.replace("```json", "").replace("```", "")
            
        return text.strip()

    def get_analysis(self, prompt_template, **kwargs):
        content = prompt_template.format(**kwargs)
        
        try:
            # 注意：deepseek-reasoner 不支持 response_format='json_object' 参数
            # 所以我们要去掉那个参数，完全靠 Prompt 约束
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": content} 
                    # R1 建议把 prompt 都放在 user 里，system prompt 权重较低
                ],
                max_tokens=self.config["llm"]["max_tokens"]
            )
            
            raw_content = response.choices[0].message.content
            
            # 1. 清洗思考过程
            clean_content = self._clean_think_tag(raw_content)
            
            # 2. 解析 JSON
            return json.loads(clean_content)

        except json.JSONDecodeError:
            print(f"❌ JSON 解析失败 (R1 可能话太多了): {clean_content[:100]}...")
            return {"score": 0.0, "reason": "模型输出格式错误", "action_advice": "观望"}
        except Exception as e:
            print(f"❌ LLM 调用失败: {e}")
            return {"score": 0.0, "reason": "API连接异常", "action_advice": "观望"}

llm_client = DeepSeekClient()