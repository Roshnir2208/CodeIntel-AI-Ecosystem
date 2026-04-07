"""
Unit tests for CodeIntel model
"""

import pytest
import json
from src.model.code_analyzer import CodeAnalyzer


@pytest.fixture
def analyzer():
    """Initialize analyzer"""
    return CodeAnalyzer()


def test_summarize_task(analyzer):
    """Test code summarization"""
    code = "def hello(): print('world')"
    result = analyzer.analyze_code(code, "summarize")
    
    assert result['task'] == 'summarize'
    assert len(result['output']) > 0
    assert result['execution_time_ms'] > 0


def test_document_task(analyzer):
    """Test documentation generation"""
    code = "def add(a, b): return a + b"
    result = analyzer.analyze_code(code, "document")
    
    assert result['task'] == 'document'
    assert len(result['output']) > 0


def test_bugs_task(analyzer):
    """Test bug detection"""
    code = "f = open('file.txt'); data = f.read()"
    result = analyzer.analyze_code(code, "bugs")
    
    assert result['task'] == 'bugs'
    assert len(result['output']) > 0


def test_optimize_task(analyzer):
    """Test optimization suggestions"""
    code = "for i in range(len(arr)): print(arr[i])"
    result = analyzer.analyze_code(code, "optimize")
    
    assert result['task'] == 'optimize'
    assert len(result['output']) > 0


def test_execution_time_recorded(analyzer):
    """Test that execution time is recorded"""
    code = "x = 1"
    result = analyzer.analyze_code(code)
    
    assert 'execution_time_ms' in result
    assert result['execution_time_ms'] > 0