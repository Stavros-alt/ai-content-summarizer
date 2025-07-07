import tkinter as tk
from tkinter import scrolledtext, messagebox
import spacy
from collections import Counter
from string import punctuation
from heapq import nlargest
import subprocess
import sys
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_tkinter():
    """Verify Tkinter is working"""
    try:
        test = tk.Tk()
        test.destroy()
        return True
    except Exception as e:
        logger.error(f"Tkinter test failed: {e}")
        return False

# --- 1. THE SUMMARIZATION ENGINE ---

# Load the spaCy model once
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    print("Downloading 'en_core_web_sm' model...")
    subprocess.run(['python', '-m', 'spacy', 'download', 'en_core_web_sm'], check=True)
    nlp = spacy.load('en_core_web_sm')

def generate_summary(text, num_sentences=3):
    """
    Generates an extractive summary of a given text using spaCy.
    """
    if not text.strip():
        return "No text provided for summarization"

    # Create a spaCy document object
    doc = nlp(text)

    # 1. Filter out stop words and punctuation
    keywords = [token.text for token in doc if not token.is_stop and not token.is_punct]

    # 2. Calculate word frequencies
    word_frequencies = Counter(keywords)
    
    if not word_frequencies:
        return "Text contains only stopwords/punctuation"

    # 3. Normalize frequencies (divide by the max frequency)
    max_frequency = max(word_frequencies.values(), default=1)
    if max_frequency == 0:
        return "No meaningful content found"

    # Create a separate dictionary for normalized frequencies
    normalized_frequencies = {
        word: float(freq) / max_frequency 
        for word, freq in word_frequencies.items()
    }

    # 4. Score sentences based on the frequency of their words
    sentence_scores = {}
    for sentence in doc.sents:
        for word in sentence:
            word_lower = word.text.lower()
            if word_lower in normalized_frequencies:
                if sentence in sentence_scores:
                    sentence_scores[sentence] += normalized_frequencies[word_lower]
                else:
                    sentence_scores[sentence] = normalized_frequencies[word_lower]

    # 5. Find the N-highest scored sentences
    summarized_sentences = nlargest(num_sentences, sentence_scores.keys(), key=lambda s: sentence_scores[s])
    
    # 6. Join them to form the final summary
    final_summary = [sentence.text for sentence in summarized_sentences]
    
    return " ".join(final_summary)
# --- 2. THE GUI APPLICATION ---
class App:
    def __init__(self, root):
        logger.info("Initializing application window")
        try:
            self.root = root
            self.root.title("AI Content Summarizer")
            self.root.geometry("800x750+0+0")  # Force position to (0,0)
            self.root.configure(bg="#34495e")
            
            # Ensure window is brought to front
            self.root.lift()
            self.root.attributes('-topmost', True)
            self.root.after_idle(self.root.attributes, '-topmost', False)
            
            logger.info("Window created at position (0,0)")

            # Create widgets
            logger.info("Creating UI widgets")
            self.create_widgets()
        except Exception as e:
            logger.error(f"GUI initialization failed: {e}")
            raise

    def create_widgets(self):
        """Create and arrange all GUI widgets"""
        # Input section
        self.input_label = tk.Label(self.root, text="Enter Text to Summarize:", bg="#34495e", fg="white")
        self.input_label.pack(pady=(10, 0))
        
        self.input_text = scrolledtext.ScrolledText(self.root, width=90, height=20, wrap=tk.WORD)
        self.input_text.pack(pady=(0, 10))

        # Controls
        self.controls_frame = tk.Frame(self.root, bg="#34495e")
        self.controls_frame.pack(pady=10, fill=tk.X)

        tk.Label(self.controls_frame, text="Number of sentences in summary:", font=("Arial", 11), bg="#34495e", fg="white").pack(side=tk.LEFT, padx=(0, 10))
        self.num_sentences_entry = tk.Entry(self.controls_frame, width=5, font=("Arial", 11))
        self.num_sentences_entry.pack(side=tk.LEFT)
        self.num_sentences_entry.insert(0, "3")  # Default value

        self.summarize_btn = tk.Button(self.controls_frame, text="SUMMARIZE NOW", command=self.on_summarize, font=("Arial", 12, "bold"), bg="#16a085", fg="white", relief=tk.FLAT)
        self.summarize_btn.pack(side=tk.LEFT, padx=20)

        self.clear_btn = tk.Button(self.controls_frame, text="Clear", command=self.on_clear)
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        # Output section
        self.output_label = tk.Label(self.root, text="Summary:", bg="#34495e", fg="white")
        self.output_label.pack(pady=(10, 0))

        self.output_text = scrolledtext.ScrolledText(self.root, width=90, height=10, wrap=tk.WORD, state="disabled")
        self.output_text.pack(pady=(0, 10))

        # Stats section
        self.stats_label = tk.Label(self.root, text="Stats:", bg="#34495e", fg="white")
        self.stats_label.pack()

        self.stats_text = tk.Text(self.root, width=90, height=2, state="disabled")
        self.stats_text.pack()

    def on_summarize(self):
        """Handle summarize button click"""
        try:
            logger.info("Starting summarization")
            input_text = self.input_text.get("1.0", tk.END).strip()
            
            if not input_text:
                messagebox.showwarning("Input Error", "Please paste some text to summarize.")
                return

            # Validate number input
            try:
                num_sents = int(self.num_sentences_entry.get())
                if num_sents <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Input Error", "Number of sentences must be a positive integer.")
                return

            summary = generate_summary(input_text, num_sents)
            
            self.output_text.config(state="normal")
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("1.0", summary)
            self.output_text.config(state="disabled")
            
            # Calculate word counts
            original_words = input_text.split()
            summary_words = summary.split()
            
            self.stats_text.config(state="normal")
            self.stats_text.delete("1.0", tk.END)
            
            if original_words:
                reduction = 100 - (len(summary_words) / len(original_words) * 100)
                stats = f"Original: {len(original_words)} words | Summary: {len(summary_words)} words | Reduction: {reduction:.1f}%"
            else:
                stats = "Original: 0 words | Summary: 0 words | Reduction: 0%"
                
            self.stats_text.insert("1.0", stats)
            self.stats_text.config(state="disabled")
            logger.info(f"Summarization complete - {stats}")
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            messagebox.showerror("Error", f"Failed to generate summary: {str(e)}")

    def on_clear(self):
        """Handle clear button click"""
        self.input_text.delete("1.0", tk.END)
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", tk.END)
        self.output_text.config(state="disabled")
        self.stats_text.config(state="normal")
        self.stats_text.delete("1.0", tk.END)
        self.stats_text.config(state="disabled")
        logger.info("Cleared all input and output")

# --- 3. RUN THE APPLICATION ---
if __name__ == "__main__":
    if not check_tkinter():
        print("ERROR: Tkinter is not working properly. Please ensure Tkinter is installed.")
        if sys.platform == "win32":
            print("On Windows, try reinstalling Python with Tkinter support")
        sys.exit(1)

    try:
        logger.info("Starting application with forced position")
        root = tk.Tk()
        app = App(root)
        logger.info("Window initialized, entering main loop")
        root.mainloop()
        logger.info("Main loop exited")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        messagebox.showerror("Fatal Error", f"Application failed to start:\n{str(e)}")

