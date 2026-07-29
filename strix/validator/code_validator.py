from __future__ import annotations
import ast
import py_compile
import subprocess
import tempfile
import os
from pathlib import Path
from strix.types import ValidationResult

class CodeValidator:
    """Validates generated code for syntax errors and basic correctness."""
    
    def __init__(self):
        print("[STRIX CodeValidator] Initialized")
        
    def detect_language(self, code: str, filename: str = '') -> str:
        """Detect language from code content or filename extension."""
        if filename:
            ext = Path(filename).suffix.lower()
            if ext == '.py': return 'python'
            if ext in ['.js', '.jsx']: return 'javascript'
            if ext == '.java': return 'java'
            if ext in ['.html', '.htm']: return 'html'
            if ext in ['.cpp', '.cxx', '.cc']: return 'cpp'
            if ext == '.c': return 'c'
            
        if 'def ' in code and 'import ' in code: return 'python'
        if 'function' in code and 'const ' in code: return 'javascript'
        if 'public class' in code and 'public static void main' in code: return 'java'
        if '<html' in code or '<body' in code: return 'html'
        
        return 'unknown'
        
    def validate(self, code: str, language: str) -> ValidationResult:
        lang = language.lower()
        if lang == 'python':
            try:
                ast.parse(code)
                with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w') as f:
                    f.write(code)
                    temp_name = f.name
                try:
                    py_compile.compile(temp_name, doraise=True)
                finally:
                    os.unlink(temp_name)
                return ValidationResult(passed=True)
            except SyntaxError as e:
                return ValidationResult(passed=False, error=str(e), warnings=[])
            except Exception as e:
                return ValidationResult(passed=False, error=str(e), warnings=[])
                
        elif lang == 'javascript':
            try:
                result = subprocess.run(['node', '-v'], capture_output=True, text=True)
                if result.returncode == 0:
                    with tempfile.NamedTemporaryFile(suffix='.js', delete=False, mode='w') as f:
                        f.write(code)
                        temp_name = f.name
                    try:
                        check = subprocess.run(['node', '--check', temp_name], capture_output=True, text=True)
                        if check.returncode == 0:
                            return ValidationResult(passed=True)
                        else:
                            return ValidationResult(passed=False, error=check.stderr)
                    finally:
                        os.unlink(temp_name)
            except FileNotFoundError:
                return ValidationResult(passed=True, warnings=["Node.js not found, skipping JS validation"])
                
        elif lang == 'java':
            if code.count('{') != code.count('}'):
                return ValidationResult(passed=False, error="Mismatched braces")
            if 'class ' not in code:
                return ValidationResult(passed=False, error="No class declaration found")
            return ValidationResult(passed=True)
            
        elif lang == 'html':
            if code.count('<') != code.count('>'):
                return ValidationResult(passed=False, error="Mismatched angle brackets")
            return ValidationResult(passed=True)
            
        else:
            return ValidationResult(passed=True, warnings=[f"No specific validation available for {language}"])
