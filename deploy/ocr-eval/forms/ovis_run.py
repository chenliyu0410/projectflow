"""Run OvisOCR2 (local GPU, transformers) over images and write {image: {"text", "seconds"}} JSON. Nothing leaves the machine.

    <ovis-python> deploy/ocr-eval/forms/ovis_run.py --model ../output/ocr-forms/models/OvisOCR2 --out result.json IMG [IMG ...]
    <ovis-python> deploy/ocr-eval/forms/ovis_run.py --model ... --out result.json --list images.txt [--prompt field|checkbox|page]

Kept apart from the evaluation code so the evaluation environment never needs torch.
"""
import argparse
import json
from pathlib import Path
import time

import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

PROMPTS = {
    # The model card's page prompt (image tags dropped from the instructions because forms have none worth keeping).
    "page": "\nExtract all readable content from the image in natural human reading order and output the result as a single "
            "Markdown document. Format tables as HTML: <table>...</table>. Transcribe all other text as standard Markdown. "
            "Preserve the original text without translation or paraphrasing.",
    "field": "\nExtract all readable content from the image in natural human reading order and output the result as a single "
             "Markdown document. Preserve the original text without translation or paraphrasing.",
    "checkbox": "\nIs this checkbox marked (ticked, crossed or filled in)? Answer with exactly one word: yes or no.",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--list", type=Path)
    parser.add_argument("--prompt", choices=PROMPTS, default="page")
    parser.add_argument("--max-new-tokens", type=int, default=2048)
    parser.add_argument("images", nargs="*")
    args = parser.parse_args()
    images = list(args.images) + (args.list.read_text(encoding="utf-8").split() if args.list else [])
    processor = AutoProcessor.from_pretrained(args.model)
    model = AutoModelForImageTextToText.from_pretrained(args.model, dtype=torch.bfloat16, device_map="cuda").eval()
    tokenizer = processor.tokenizer
    # Without <|im_end|> as a stop token the model ends its turn and keeps writing new ones until max_new_tokens.
    stop = sorted({tokenizer.convert_tokens_to_ids("<|im_end|>"), tokenizer.eos_token_id} - {None})
    results = json.loads(args.out.read_text(encoding="utf-8")) if args.out.is_file() else {}
    for path in images:
        if path in results:
            continue
        image = Image.open(path).convert("RGB")
        messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": PROMPTS[args.prompt]}]}]
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        inputs = processor(text=[text], images=[image], return_tensors="pt",
                           images_kwargs={"min_pixels": 64 * 64 if args.prompt != "page" else 448 * 448,
                                          "max_pixels": 2880 * 2880}).to("cuda")
        torch.cuda.synchronize()
        started = time.perf_counter()
        with torch.inference_mode():
            output = model.generate(**inputs, max_new_tokens=args.max_new_tokens if args.prompt != "checkbox" else 4,
                                    do_sample=False, eos_token_id=stop)
        torch.cuda.synchronize()
        answer = processor.batch_decode(output[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0]
        answer = answer.split("<think>")[0].strip()
        results[path] = {"text": answer, "seconds": round(time.perf_counter() - started, 3)}
        if len(results) % 20 == 0:
            args.out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    args.out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(results)} results in {args.out}; peak GPU memory {torch.cuda.max_memory_allocated() / 2**30:.2f} GiB")


if __name__ == "__main__":
    main()
