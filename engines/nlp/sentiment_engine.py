import os

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

class FinBERTSentimentEngine:
    """
    NLP Engine using ProsusAI/finbert for financial sentiment analysis.
    """
    def __init__(self, use_local_cache=True):
        self.model_name = "ProsusAI/finbert"
        self.tokenizer = None
        self.model = None
        self.is_loaded = False
        
        # Determine paths
        self.cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_cache")
        if use_local_cache and os.path.exists(self.cache_dir) and len(os.listdir(self.cache_dir)) > 0:
            self.load_path = self.cache_dir
        else:
            self.load_path = self.model_name
            
    def load(self):
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("PyTorch and Transformers are required for FinBERT. Run: pip install torch transformers")
            
        print(f"Loading FinBERT model from: {self.load_path}")
        
        # Load tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(self.load_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.load_path)
        
        # Move to GPU if available
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        self.model.eval() # Set to evaluation mode
        
        self.is_loaded = True
        
    def save_local(self):
        """Caches the downloaded HuggingFace model locally to prevent redownloads."""
        if not self.is_loaded:
            raise ValueError("Model must be loaded before saving.")
            
        os.makedirs(self.cache_dir, exist_ok=True)
        print(f"Saving model locally to {self.cache_dir}...")
        self.tokenizer.save_pretrained(self.cache_dir)
        self.model.save_pretrained(self.cache_dir)
        print("Save complete.")

    def score_text(self, text: str):
        """
        Takes a headline or paragraph and returns the sentiment probabilities.
        Returns a dictionary: {"positive": float, "negative": float, "neutral": float, "dominant": str}
        """
        if not self.is_loaded:
            self.load()
            
        if not TRANSFORMERS_AVAILABLE:
            return {"positive": 0.33, "negative": 0.33, "neutral": 0.34, "dominant": "neutral", "error": "Transformers missing"}
            
        inputs = self.tokenizer(text, padding=True, truncation=True, return_tensors='pt').to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            
        # FinBERT outputs 3 classes: [positive, negative, neutral]
        probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1).squeeze().tolist()
        
        labels = ["positive", "negative", "neutral"]
        scores = {label: prob for label, prob in zip(labels, probabilities)}
        
        dominant = max(scores, key=scores.get)
        scores["dominant"] = dominant
        
        return scores
