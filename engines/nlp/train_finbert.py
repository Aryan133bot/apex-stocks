import os
import sys

# Add the root directory to path for absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engines.nlp.sentiment_engine import FinBERTSentimentEngine

def train_and_validate_finbert():
    print("=== APEX NLP MODULE: FinBERT Initialization ===")
    print("1. Downloading / Loading ProsusAI/finbert Weights...")
    
    engine = FinBERTSentimentEngine(use_local_cache=False) # Force initial download from HF
    engine.load()
    
    print("\n2. Caching model locally for instant offline execution...")
    engine.save_local()
    
    print("\n3. Validating Model Inference on Test Set...")
    
    test_headlines = [
        "Reliance Industries reports a massive 25% jump in Q4 net profits, beating street estimates.",
        "Inflation fears spark a major sell-off in IT and banking stocks across the NSE.",
        "Tata Motors announces a new line of EV vehicles; revenue guidance remains unchanged.",
        "HDFC Bank management warns of rising non-performing assets in the retail loan book.",
        "SEBI approves the new regulatory framework for SME IPOs."
    ]
    
    for i, text in enumerate(test_headlines, 1):
        result = engine.score_text(text)
        print(f"\nHeadline {i}: {text}")
        print(f"  Dominant Sentiment: {result['dominant'].upper()}")
        print(f"  Probabilities: +{result['positive']:.2%} | -{result['negative']:.2%} | ={result['neutral']:.2%}")
        
    print("\n=== FinBERT Training & Validation Complete ===")

if __name__ == "__main__":
    train_and_validate_finbert()
