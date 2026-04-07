"""
CodeIntel - Advanced Code Analysis Model
Uses CodeT5+ for multi-task code understanding
"""

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import json
from typing import Dict, List
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CodeAnalyzer:
    def __init__(self, model_name="Salesforce/codet5p-770m"):
        """Initialize CodeT5+ model for code analysis tasks"""
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"Loading {model_name} on {self.device}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name,
            torch_dtype=torch.float32,
            device_map="auto"
        )
        self.model.eval()
        
    def analyze_code(self, code_snippet: str, task_type: str = "summarize") -> Dict:
        """
        Analyze code for various tasks:
        - summarize: Generate code summary
        - document: Generate documentation
        - bugs: Detect potential bugs
        - optimize: Suggest optimizations
        """
        
        task_prefix = {
            "summarize": "summarize:",
            "document": "document:",
            "bugs": "find bugs:",
            "optimize": "optimize:"
        }
        
        if task_type not in task_prefix:
            task_type = "summarize"
        
        input_text = f"{task_prefix[task_type]} {code_snippet}"
        
        start_time = time.time()
        
        inputs = self.tokenizer(
            input_text,
            max_length=512,
            truncation=True,
            return_tensors="pt"
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=256,
                num_beams=4,
                early_stopping=True,
                temperature=0.7
            )
        
        result = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        execution_time = (time.time() - start_time) * 1000  # ms
        
        return {
            "task": task_type,
            "input_length": len(code_snippet),
            "output": result,
            "confidence": 0.85,
            "execution_time_ms": execution_time
        }
    
    def batch_analyze(self, code_samples: List[Dict]) -> List[Dict]:
        """Batch process multiple code samples"""
        results = []
        for sample in code_samples:
            result = self.analyze_code(
                sample.get("code", ""),
                sample.get("task", "summarize")
            )
            result["sample_id"] = sample.get("id", "unknown")
            results.append(result)
        
        return results


if __name__ == "__main__":
    # Test the model
    analyzer = CodeAnalyzer()
    
    test_code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
    """
    
    result = analyzer.analyze_code(test_code, "summarize")
    print(json.dumps(result, indent=2))