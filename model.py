import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

_MODEL = None
_TOKENIZER = None

_MODEL_ID = "microsoft/phi-2"

# Must match tool label in prompt_builder when a tool returned data
_TOOL_RESULT_MARKER = "Tool Result:"


def _load_model() -> None:
    global _MODEL, _TOKENIZER
    if _MODEL is not None:
        return

    _TOKENIZER = AutoTokenizer.from_pretrained(_MODEL_ID)
    if _TOKENIZER.pad_token is None:
        _TOKENIZER.pad_token = _TOKENIZER.eos_token

    _MODEL = AutoModelForCausalLM.from_pretrained(
        _MODEL_ID,
        torch_dtype=torch.float16,
        device_map="auto",
    )
    _MODEL.eval()
    print("Model loaded successfully")


def generate_response(prompt: str) -> str:
    _load_model()

    system = (
        "You are a helpful assistant. Always reply in English only. "
        "Keep replies short and direct."
    )

    if _TOOL_RESULT_MARKER in prompt:
        input_text = f"{system}\n\n{prompt}\nAnswer:"
    else:
        input_text = f"{system}\n\nUser: {prompt}\nAssistant:"

    inputs = _TOKENIZER(input_text, return_tensors="pt")
    device = next(_MODEL.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.inference_mode():
        output_ids = _MODEL.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.7,
            top_p=0.95,
            do_sample=True,
            repetition_penalty=1.3,
        )

    input_len = inputs["input_ids"].shape[-1]
    new_tokens = output_ids[0][input_len:]
    response = _TOKENIZER.decode(new_tokens, skip_special_tokens=True).strip()
    return response
