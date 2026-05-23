"""
host_app/multimodal_agent.py
Unified Perceptual Agent: Integrates CV matrices and raw sensor telemetry 
using a local Vision-Language Model to ground language in physical metrics.
"""

import os
import cv2
import ollama

class UnifiedEmbodiedAgent:
    def __init__(self, model_name: str = "moondream"):
        self.model_name = model_name
        self._warmup()

    def _warmup(self):
        """Checks if ollama is running and has the model pulled."""
        try:
            # Simple check to confirm the model is available
            ollama.show(self.model_name)
        except Exception:
            print(f"[Agent] Warning: Could not find '{self.model_name}' locally. Please run 'ollama pull {self.model_name}'")

    def generate_grounded_summary(self, frame, accel_g: float, fft_hz: int, heuristic_state: str) -> str:
        """
        Ingests vision frame, audio bins, and tactile forces simultaneously 
        to synthesize an embodied description.
        """
        if frame is None:
            return "Sensory error: Egocentric vision array is currently blank."

        # Save the current frame to a temporary image file for Ollama to process
        temp_img_path = "temp_agent_view.jpg"
        cv2.imwrite(temp_img_path, frame)

        # Construct the late-fusion multi-modal context prompt
        prompt = f"""
        System: You are an integrated physical AI agent exploring forest debris (sticks and leaves).
        
        [TACTILE & AUDIO REAL-TIME FEEDS]
        - Structural Vibration Impact: {accel_g:.2f} g
        - Acoustic Dominant Resonance: {fft_hz} Hz
        - Underlying Low-Level Classifier State: {heuristic_state}
        
        Task: Observe the attached camera image. Synthesize what you see with the 
        vibrational/acoustic metrics above. Provide a concise, 2-sentence summary 
        of what you are 'seeing and feeling'. Explain how the sound and physical touch 
        properties correlate with or support the visual identification of the material.
        """

        try:
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                images=[temp_img_path]
            )
            summary = response['response'].strip()
        except Exception as e:
            summary = f"Perceptual parsing failed: {str(e)}"
        finally:
            if os.path.exists(temp_img_path):
                os.remove(temp_img_path)

        return summary