import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel
from typing import Optional, List

from src.utils.settings import MODEL_NAME, MAX_SEQUENCE_LENGTH, DEVICE

class EmbeddingGenerator:
    """Class for generating embeddings using BERT."""
    
    def __init__(self):
        """Initialize the BERT model and tokenizer."""
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.model = AutoModel.from_pretrained(MODEL_NAME)
        self.model.to(DEVICE)
        self.model.eval()
    
    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Generate embedding for text using BERT.
        
        Args:
            text (str): Text to embed
            
        Returns:
            Optional[np.ndarray]: 768-dimensional embedding vector or None if error
        """
        try:
            # Tokenize text
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                max_length=MAX_SEQUENCE_LENGTH,
                truncation=True,
                padding=True
            )
            inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
            
            # Generate embeddings
            with torch.no_grad():
                outputs = self.model(**inputs)
                # Use [CLS] token embedding as sentence representation
                embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy()
            
            # Normalize the embedding
            embedding = embedding[0]  # Remove batch dimension
            embedding = embedding / np.linalg.norm(embedding)
            
            return embedding
            
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
    
    def batch_get_embeddings(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts (List[str]): List of texts to embed
            
        Returns:
            List[Optional[np.ndarray]]: List of embeddings or None for failed texts
        """
        embeddings = []
        for text in texts:
            embedding = self.get_embedding(text)
            embeddings.append(embedding)
        return embeddings 