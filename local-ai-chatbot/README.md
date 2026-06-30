# Local AI Chatbot

This project trains a small Transformer language model from random weights. It
does not call an API, download pretrained model weights, or send conversations
to an online AI service.

## What is included

- A byte-level tokenizer written locally
- A decoder-only Transformer written with PyTorch
- GPU training with mixed precision
- Local checkpoints containing your own learned weights
- A terminal chat program with short conversation memory

The sample dataset only proves that the system works. A useful general chatbot
requires a much larger, carefully prepared dataset.

## 1. Install Python

Install 64-bit Python 3.11 or 3.12 from:

https://www.python.org/downloads/

During installation, select **Add python.exe to PATH**.

## 2. Set up the project

Open PowerShell in this folder and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup.ps1
```

This creates an isolated `.venv` folder and installs the CUDA 12.8 build of
PyTorch for the NVIDIA GPU.

Verify that PyTorch can see the RTX 3060 Ti:

```powershell
.\.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

## 3. Add training data

Edit `data/training.txt`. Keep conversational examples in this form:

```text
User: How do I learn programming?
Assistant: Begin with one language, practice small projects, and get comfortable reading error messages.
```

You may also add ordinary prose, articles, notes, and other text that you own or
have permission to use. Quality and variety matter more than repeating the same
examples.

## 4. Train

First run a short test:

```powershell
.\.venv\Scripts\python.exe train.py --steps 100
```

Then run a longer training session:

```powershell
.\.venv\Scripts\python.exe train.py --steps 5000
```

The RTX 3060 Ti defaults are deliberately modest: a roughly 11-million-parameter
model, 512-token context, mixed precision, and gradient accumulation. If GPU
memory runs out, reduce `--batch-size` to 4 or `--context-length` to 256.

The latest model is saved at `checkpoints/latest.pt`.

## 5. Chat

### Webpage

Run:

```powershell
.\start_nova.ps1
```

Then open http://127.0.0.1:8000 in a browser. Keep the PowerShell window open
while chatting. The website and model both run locally on this computer.

### Terminal

```powershell
.\.venv\Scripts\python.exe chat.py --name Nova
```

Use `/reset` to clear the conversation and `/quit` to exit.

## Useful experiments

Smaller, faster model:

```powershell
.\.venv\Scripts\python.exe train.py --steps 1000 --d-model 256 --heads 4 --layers 4 --context-length 256
```

Change response randomness:

```powershell
.\.venv\Scripts\python.exe chat.py --temperature 0.6
```

Lower temperatures are more predictable. Higher temperatures are more varied
but more likely to produce nonsense.

## Reality check

This is a real language model, but the included training text is tiny. It will
mostly imitate the sample data and may initially produce broken text. Building
something broadly knowledgeable requires millions or billions of good tokens,
many training runs, evaluation, and substantially more computing power.
