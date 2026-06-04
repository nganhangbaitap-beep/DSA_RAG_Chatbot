from core.embedder import GeminiEmbedder

e = GeminiEmbedder()

print("Testing...")
vec = e.embed_query("hello")

print("OK:", len(vec))