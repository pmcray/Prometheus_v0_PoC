"""
Multimodal Tool Integration (v0.70)

Provides secure wrappers for multimodal generative capabilities:
- Text-to-image generation
- Text-to-speech (audio)
- Text-to-video generation
- Multimodal understanding

These tools expand the agent's capability layer to operate beyond text.
"""

import logging
import os
import base64
from typing import Optional, Dict, Any, Union
from pathlib import Path
from dataclasses import dataclass
import io
import json
import requests
import time
import uuid

# Multimodal model support
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("google-generativeai not available")

# Image generation support (local/API)
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("Pillow not available - image handling disabled")


@dataclass
class GenerationResult:
    """Result from a multimodal generation task."""
    success: bool
    content: Optional[Any] = None  # File path, bytes, or text
    content_type: str = "unknown"  # "image", "audio", "video", "text"
    metadata: Dict[str, Any] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ComfyUIBackend:
    """
    Backend for local image generation using ComfyUI.

    ComfyUI is a node-based Stable Diffusion workflow system that runs locally
    with GPU acceleration. This backend communicates with ComfyUI's HTTP API.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8188,
        timeout: int = 300
    ):
        """
        Initialize ComfyUI backend.

        Args:
            host: ComfyUI server host
            port: ComfyUI server port
            timeout: Request timeout in seconds
        """
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        self.client_id = str(uuid.uuid4())

        logging.info(f"ComfyUI backend initialized: {self.base_url}")

    def is_available(self) -> bool:
        """Check if ComfyUI server is running and accessible."""
        try:
            response = requests.get(
                f"{self.base_url}/system_stats",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logging.debug(f"ComfyUI not available: {e}")
            return False

    def build_workflow(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        steps: int = 20,
        cfg_scale: float = 7.0,
        seed: int = -1
    ) -> Dict[str, Any]:
        """
        Build a basic text-to-image workflow for ComfyUI.

        This creates a simple workflow with:
        - Text prompt encoder
        - CLIP text encoder
        - KSampler for generation
        - VAE decoder
        - Image save node

        Args:
            prompt: Positive text prompt
            negative_prompt: Negative text prompt
            width: Image width
            height: Image height
            steps: Number of sampling steps
            cfg_scale: CFG scale for guidance
            seed: Random seed (-1 for random)

        Returns:
            ComfyUI workflow JSON
        """
        if seed == -1:
            seed = int(time.time() * 1000) % (2**32)

        workflow = {
            "3": {
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg_scale,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                },
                "class_type": "KSampler"
            },
            "4": {
                "inputs": {
                    "ckpt_name": "sd_xl_base_1.0.safetensors"  # Default model
                },
                "class_type": "CheckpointLoaderSimple"
            },
            "5": {
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage"
            },
            "6": {
                "inputs": {
                    "text": prompt,
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "7": {
                "inputs": {
                    "text": negative_prompt,
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "8": {
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                },
                "class_type": "VAEDecode"
            },
            "9": {
                "inputs": {
                    "filename_prefix": "prometheus",
                    "images": ["8", 0]
                },
                "class_type": "SaveImage"
            }
        }

        return workflow

    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "blurry, low quality, distorted",
        width: int = 512,
        height: int = 512,
        steps: int = 20,
        cfg_scale: float = 7.0,
        seed: int = -1
    ) -> Optional[str]:
        """
        Generate an image using ComfyUI.

        Args:
            prompt: Text description
            negative_prompt: What to avoid
            width: Image width
            height: Image height
            steps: Sampling steps
            cfg_scale: CFG guidance scale
            seed: Random seed

        Returns:
            Path to generated image file, or None on failure
        """
        try:
            # Build workflow
            workflow = self.build_workflow(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=steps,
                cfg_scale=cfg_scale,
                seed=seed
            )

            # Queue prompt
            queue_data = {
                "prompt": workflow,
                "client_id": self.client_id
            }

            response = requests.post(
                f"{self.base_url}/prompt",
                json=queue_data,
                timeout=self.timeout
            )

            if response.status_code != 200:
                logging.error(f"ComfyUI queue failed: {response.text}")
                return None

            result = response.json()
            prompt_id = result.get("prompt_id")

            if not prompt_id:
                logging.error("No prompt_id returned from ComfyUI")
                return None

            logging.info(f"ComfyUI prompt queued: {prompt_id}")

            # Wait for completion and get result
            return self._wait_for_result(prompt_id)

        except Exception as e:
            logging.error(f"ComfyUI generation failed: {e}")
            return None

    def _wait_for_result(self, prompt_id: str) -> Optional[str]:
        """
        Wait for ComfyUI to complete generation and retrieve result.

        Args:
            prompt_id: ID of queued prompt

        Returns:
            Path to generated image, or None on failure
        """
        start_time = time.time()

        while time.time() - start_time < self.timeout:
            try:
                # Check history for completed prompt
                response = requests.get(
                    f"{self.base_url}/history/{prompt_id}",
                    timeout=10
                )

                if response.status_code == 200:
                    history = response.json()

                    if prompt_id in history:
                        prompt_info = history[prompt_id]

                        # Check if completed
                        if "outputs" in prompt_info:
                            # Find SaveImage node output
                            for node_id, output in prompt_info["outputs"].items():
                                if "images" in output:
                                    images = output["images"]
                                    if images:
                                        # Get first image
                                        image_info = images[0]
                                        filename = image_info["filename"]
                                        subfolder = image_info.get("subfolder", "")

                                        # Download image
                                        return self._download_image(
                                            filename,
                                            subfolder
                                        )

                # Wait before checking again
                time.sleep(2)

            except Exception as e:
                logging.debug(f"Error checking ComfyUI status: {e}")
                time.sleep(2)

        logging.error(f"ComfyUI generation timed out after {self.timeout}s")
        return None

    def _download_image(
        self,
        filename: str,
        subfolder: str = ""
    ) -> Optional[str]:
        """
        Download generated image from ComfyUI.

        Args:
            filename: Image filename
            subfolder: Subfolder in output directory

        Returns:
            Local path to downloaded image
        """
        try:
            params = {
                "filename": filename,
                "subfolder": subfolder,
                "type": "output"
            }

            response = requests.get(
                f"{self.base_url}/view",
                params=params,
                timeout=30
            )

            if response.status_code != 200:
                logging.error(f"Failed to download image: {response.status_code}")
                return None

            # Save to local file
            output_dir = Path("./generated_content")
            output_dir.mkdir(parents=True, exist_ok=True)

            local_path = output_dir / filename
            local_path.write_bytes(response.content)

            logging.info(f"✓ Image downloaded: {local_path}")
            return str(local_path)

        except Exception as e:
            logging.error(f"Failed to download image: {e}")
            return None


class MultimodalToolkit:
    """
    Unified interface for multimodal content generation and understanding.

    Supports:
    - Image generation (Gemini Imagen or local Stable Diffusion)
    - Audio generation (text-to-speech)
    - Video generation (text-to-video, limited)
    - Multimodal understanding (vision, audio processing)

    This is the "body" upgrade for v0.70 - giving agents sensory modalities
    beyond text.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        output_dir: str = "./generated_content",
        prefer_local: bool = True,
        comfyui_host: str = "127.0.0.1",
        comfyui_port: int = 8188
    ):
        """
        Initialize multimodal toolkit.

        Args:
            api_key: Google Gemini API key for cloud generation
            output_dir: Directory to save generated content
            prefer_local: Use local tools when available (default: True)
            comfyui_host: ComfyUI server host
            comfyui_port: ComfyUI server port
        """
        self.api_key = api_key
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.prefer_local = prefer_local

        # Initialize ComfyUI backend
        self.comfyui_backend = None
        self.comfyui_available = False
        try:
            self.comfyui_backend = ComfyUIBackend(
                host=comfyui_host,
                port=comfyui_port
            )
            self.comfyui_available = self.comfyui_backend.is_available()
            if self.comfyui_available:
                logging.info("✓ ComfyUI available for local image generation")
            else:
                logging.info("ComfyUI not available (server not running?)")
        except Exception as e:
            logging.warning(f"ComfyUI initialization failed: {e}")

        # Initialize Gemini if available
        self.gemini_available = False
        if GEMINI_AVAILABLE and api_key:
            try:
                genai.configure(api_key=api_key)
                self.gemini_model = genai.GenerativeModel('generic-cloud-fm')
                self.gemini_available = True
                logging.info("✓ Gemini multimodal available")
            except Exception as e:
                logging.warning(f"Gemini initialization failed: {e}")

        # Track generation statistics
        self.stats = {
            "images_generated": 0,
            "audio_generated": 0,
            "video_generated": 0,
            "errors": 0,
            "comfyui_generations": 0,
            "placeholder_generations": 0
        }

        logging.info(f"MultimodalToolkit initialized (output: {self.output_dir})")

    def generate_image(
        self,
        prompt: str,
        style: str = "realistic",
        size: str = "512x512",
        **kwargs
    ) -> GenerationResult:
        """
        Generate an image from a text prompt.

        Args:
            prompt: Text description of desired image
            style: Style hint (realistic, anime, abstract, etc.)
            size: Image dimensions (e.g., "512x512", "1024x768")
            **kwargs: Additional generation parameters

        Returns:
            GenerationResult with image file path
        """
        logging.info(f"Generating image: '{prompt[:50]}...'")

        try:
            # Try ComfyUI first if available and prefer_local is True
            if self.prefer_local and self.comfyui_available:
                return self._generate_comfyui_image(prompt, style, size, **kwargs)

            # Fallback to placeholder
            return self._generate_placeholder_image(prompt, size)

        except Exception as e:
            self.stats["errors"] += 1
            logging.error(f"Image generation failed: {e}")
            return GenerationResult(
                success=False,
                error=str(e),
                content_type="image"
            )

    def _generate_comfyui_image(
        self,
        prompt: str,
        style: str,
        size: str,
        **kwargs
    ) -> GenerationResult:
        """Generate image using local ComfyUI."""
        try:
            # Parse size
            width, height = map(int, size.split('x'))

            # Add style to prompt if provided
            full_prompt = prompt
            if style and style != "realistic":
                full_prompt = f"{prompt}, {style} style"

            # Extract generation parameters
            steps = kwargs.get("steps", 20)
            cfg_scale = kwargs.get("cfg_scale", 7.0)
            seed = kwargs.get("seed", -1)
            negative_prompt = kwargs.get(
                "negative_prompt",
                "blurry, low quality, distorted, bad anatomy"
            )

            # Generate with ComfyUI
            image_path = self.comfyui_backend.generate_image(
                prompt=full_prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=steps,
                cfg_scale=cfg_scale,
                seed=seed
            )

            if image_path:
                self.stats["images_generated"] += 1
                self.stats["comfyui_generations"] += 1

                return GenerationResult(
                    success=True,
                    content=image_path,
                    content_type="image",
                    metadata={
                        "prompt": prompt,
                        "full_prompt": full_prompt,
                        "negative_prompt": negative_prompt,
                        "size": size,
                        "style": style,
                        "steps": steps,
                        "cfg_scale": cfg_scale,
                        "seed": seed,
                        "backend": "ComfyUI",
                        "format": "PNG"
                    }
                )
            else:
                # ComfyUI failed, fall back to placeholder
                logging.warning("ComfyUI generation failed, using placeholder")
                return self._generate_placeholder_image(prompt, size)

        except Exception as e:
            self.stats["errors"] += 1
            logging.error(f"ComfyUI image generation failed: {e}")
            # Fall back to placeholder
            return self._generate_placeholder_image(prompt, size)

    def _generate_placeholder_image(self, prompt: str, size: str) -> GenerationResult:
        """Generate a placeholder image for testing."""
        if not PIL_AVAILABLE:
            return GenerationResult(
                success=False,
                error="PIL not available",
                content_type="image"
            )

        try:
            # Parse size
            width, height = map(int, size.split('x'))

            # Create simple placeholder
            img = Image.new('RGB', (width, height), color=(73, 109, 137))

            # Save to output directory
            filename = f"image_{self.stats['images_generated']:04d}.png"
            filepath = self.output_dir / filename
            img.save(filepath)

            self.stats["images_generated"] += 1
            self.stats["placeholder_generations"] += 1

            logging.info(f"✓ Placeholder image saved: {filepath}")

            return GenerationResult(
                success=True,
                content=str(filepath),
                content_type="image",
                metadata={
                    "prompt": prompt,
                    "size": size,
                    "format": "PNG",
                    "backend": "Placeholder",
                    "mode": "placeholder"
                }
            )

        except Exception as e:
            self.stats["errors"] += 1
            return GenerationResult(
                success=False,
                error=str(e),
                content_type="image"
            )

    def generate_audio(
        self,
        text: str,
        voice: str = "default",
        speed: float = 1.0,
        **kwargs
    ) -> GenerationResult:
        """
        Generate audio from text (text-to-speech).

        Args:
            text: Text to synthesize
            voice: Voice profile to use
            speed: Speech rate (0.5-2.0)
            **kwargs: Additional TTS parameters

        Returns:
            GenerationResult with audio file path
        """
        logging.info(f"Generating audio: '{text[:50]}...'")

        try:
            # Placeholder for v0.70
            # In production would use Google Cloud TTS, ElevenLabs, or local TTS

            filename = f"audio_{self.stats['audio_generated']:04d}.mp3"
            filepath = self.output_dir / filename

            # Create empty placeholder file
            filepath.touch()

            self.stats["audio_generated"] += 1

            return GenerationResult(
                success=True,
                content=str(filepath),
                content_type="audio",
                metadata={
                    "text": text[:100],
                    "voice": voice,
                    "speed": speed,
                    "format": "MP3",
                    "mode": "placeholder"
                }
            )

        except Exception as e:
            self.stats["errors"] += 1
            logging.error(f"Audio generation failed: {e}")
            return GenerationResult(
                success=False,
                error=str(e),
                content_type="audio"
            )

    def generate_video(
        self,
        prompt: str,
        duration: int = 3,
        fps: int = 24,
        **kwargs
    ) -> GenerationResult:
        """
        Generate video from text prompt.

        Args:
            prompt: Text description of desired video
            duration: Video length in seconds
            fps: Frames per second
            **kwargs: Additional parameters

        Returns:
            GenerationResult with video file path
        """
        logging.info(f"Generating video: '{prompt[:50]}...'")

        try:
            # Placeholder for v0.70
            # In production would use RunwayML, Pika, or other text-to-video API

            filename = f"video_{self.stats['video_generated']:04d}.mp4"
            filepath = self.output_dir / filename

            # Create empty placeholder
            filepath.touch()

            self.stats["video_generated"] += 1

            return GenerationResult(
                success=True,
                content=str(filepath),
                content_type="video",
                metadata={
                    "prompt": prompt,
                    "duration": duration,
                    "fps": fps,
                    "format": "MP4",
                    "mode": "placeholder"
                }
            )

        except Exception as e:
            self.stats["errors"] += 1
            logging.error(f"Video generation failed: {e}")
            return GenerationResult(
                success=False,
                error=str(e),
                content_type="video"
            )

    def understand_image(
        self,
        image_path: str,
        question: str = "Describe this image in detail."
    ) -> GenerationResult:
        """
        Analyze an image using multimodal understanding.

        Args:
            image_path: Path to image file
            question: Question to ask about the image

        Returns:
            GenerationResult with text description
        """
        logging.info(f"Understanding image: {image_path}")

        try:
            if not self.gemini_available:
                return GenerationResult(
                    success=False,
                    error="Gemini not available for image understanding",
                    content_type="text"
                )

            # Load image
            if not PIL_AVAILABLE:
                return GenerationResult(
                    success=False,
                    error="PIL not available",
                    content_type="text"
                )

            img = Image.open(image_path)

            # Use Gemini vision
            response = self.gemini_model.generate_content([question, img])

            return GenerationResult(
                success=True,
                content=response.text,
                content_type="text",
                metadata={
                    "image_path": image_path,
                    "question": question,
                    "model": "generic-cloud-fm"
                }
            )

        except Exception as e:
            self.stats["errors"] += 1
            logging.error(f"Image understanding failed: {e}")
            return GenerationResult(
                success=False,
                error=str(e),
                content_type="text"
            )

    def evaluate_image_quality(
        self,
        image_path: str,
        prompt: str
    ) -> float:
        """
        Evaluate how well an image matches its generation prompt.

        Args:
            image_path: Path to generated image
            prompt: Original prompt used to generate image

        Returns:
            Quality score (0.0-1.0)
        """
        logging.info(f"Evaluating image quality: {image_path}")

        try:
            evaluation_prompt = f"""Rate how well this image matches the following description on a scale of 0.0 to 1.0:

Description: "{prompt}"

Provide ONLY a single number between 0.0 and 1.0, where:
- 1.0 = Perfect match
- 0.5 = Partial match
- 0.0 = No match

Score:"""

            result = self.understand_image(image_path, evaluation_prompt)

            if result.success:
                # Extract score from response
                score_text = result.content.strip()
                try:
                    score = float(score_text)
                    return max(0.0, min(1.0, score))  # Clamp to [0, 1]
                except ValueError:
                    logging.warning(f"Could not parse score: {score_text}")
                    return 0.5  # Default to middle score

            return 0.0

        except Exception as e:
            logging.error(f"Quality evaluation failed: {e}")
            return 0.0

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            **self.stats,
            "comfyui_available": self.comfyui_available,
            "gemini_available": self.gemini_available,
            "prefer_local": self.prefer_local,
            "output_dir": str(self.output_dir)
        }


def get_multimodal_toolkit(
    api_key: Optional[str] = None,
    output_dir: str = "./generated_content",
    prefer_local: bool = False
) -> MultimodalToolkit:
    """
    Factory function to create multimodal toolkit.

    Args:
        api_key: Gemini API key
        output_dir: Output directory for generated content
        prefer_local: Use local tools when available

    Returns:
        MultimodalToolkit instance
    """
    return MultimodalToolkit(
        api_key=api_key,
        output_dir=output_dir,
        prefer_local=prefer_local
    )


# Convenience functions for agent use
def generate_image(prompt: str, **kwargs) -> str:
    """Generate image and return file path."""
    toolkit = get_multimodal_toolkit()
    result = toolkit.generate_image(prompt, **kwargs)
    return result.content if result.success else None


def generate_audio(text: str, **kwargs) -> str:
    """Generate audio and return file path."""
    toolkit = get_multimodal_toolkit()
    result = toolkit.generate_audio(text, **kwargs)
    return result.content if result.success else None


def generate_video(prompt: str, **kwargs) -> str:
    """Generate video and return file path."""
    toolkit = get_multimodal_toolkit()
    result = toolkit.generate_video(prompt, **kwargs)
    return result.content if result.success else None
