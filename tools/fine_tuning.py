from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
import torch
from datasets import Dataset

# Load your dataset (example)
data = {
    "question": ["How to implement a class in C#?", "What is XAML used for?"],
    "answer": ["Here's a C# class example: public class Example {...}", "XAML is used for UI design in WPF applications."]
}
dataset = Dataset.from_dict(data)

# Load model and tokenizer
model_name = "qwen2.5-coder:3b"  # Adjust based on your Ollama model
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Tokenize dataset
def tokenize_function(examples):
    return tokenizer(examples["question"], padding="max_length", truncation=True)

tokenized_datasets = dataset.map(tokenize_function, batched=True)

# Training arguments
training_args = TrainingArguments(
    output_dir="./results",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    save_steps=10_000,
    save_total_limit=2,
)

# Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets,
)

# Train
trainer.train()