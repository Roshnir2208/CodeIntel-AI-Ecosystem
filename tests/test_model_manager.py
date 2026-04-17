from src.model import ModelManager


class StubTokenizer:
    eos_token = "<eos>"
    eos_token_id = 0
    pad_token = None

    @classmethod
    def from_pretrained(cls, model_name: str):
        return cls()

    def __call__(self, text, **kwargs):
        return {"input_ids": [1, 2, 3]}

    def decode(self, output, skip_special_tokens=True):
        return "def add(a, b): return a + b"

    def batch_decode(self, outputs, skip_special_tokens=True):
        return ["def a(): pass", "def b(): pass"]


class StubTensor:
    def to(self, *_args, **_kwargs):
        return self


class StubTorch:
    class cuda:
        @staticmethod
        def is_available():
            return False

    class no_grad:
        def __enter__(self):
            return None

        def __exit__(self, *args):
            return False


class StubModel:
    @classmethod
    def from_pretrained(cls, model_name: str):
        return cls()

    def eval(self):
        return None

    def generate(self, **kwargs):
        return [[1, 2, 3]]


def test_complete_validation_errors():
    manager = ModelManager()
    try:
        manager.complete("")
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_complete_with_stubs(monkeypatch):
    monkeypatch.setattr("src.model.manager.GPT2Tokenizer", StubTokenizer)
    monkeypatch.setattr("src.model.manager.GPT2LMHeadModel", StubModel)
    monkeypatch.setattr("src.model.manager.torch", StubTorch)

    manager = ModelManager(model_name="stub")
    result = manager.complete("def add(a, b):")

    assert "completion" in result
    assert result["model"] == "stub"


def test_batch_complete_validation(monkeypatch):
    monkeypatch.setattr("src.model.manager.GPT2Tokenizer", StubTokenizer)
    monkeypatch.setattr("src.model.manager.GPT2LMHeadModel", StubModel)
    monkeypatch.setattr("src.model.manager.torch", StubTorch)

    manager = ModelManager(model_name="stub")
    results = manager.batch_complete(["def a():", "def b():"])

    assert len(results) == 2
