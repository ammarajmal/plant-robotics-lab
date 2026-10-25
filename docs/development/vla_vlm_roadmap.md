# VLM / VLA / imitation-learning roadmap

Status of everything here: **proposed**. Nothing below is installed or tested in PRL. Figures come from web search on 2026-10-25 (secondary blogs and papers; sources disagree), so confirm each against the official repo before spending time or money. Hardware: RTX 4070, 12 GB.

## Fit for a 12 GB GPU

| Model | Role | Local on 12 GB? | Basis |
|---|---|---|---|
| ACT | Imitation baseline (M6) | Yes, expected | In LeRobot; small |
| Diffusion Policy | Alternative baseline | Yes, expected | In LeRobot |
| SmolVLA | First VLA to try | Inference yes; training only with a frozen vision encoder, small batch, and not confirmed | A LeRobot v0.6.0 guide estimates 10-16 GB peak |
| pi0 / pi0.5 | Large VLA | No for training | Guides cite A100 40 GB; openpi LoRA about 22.5 GB (JAX path); full fine-tune over 70 GB |
| OpenVLA (7B) | Large VLA | No for training | Official LoRA: about 27 GB minimum, 72 GB at batch 16 |
| GR00T N1.x | NVIDIA VLA | Inference maybe (16 GB baseline); no for fine-tuning | NVIDIA baseline 40 GB+ for fine-tuning |
| Mobile ALOHA | Bimanual hardware and co-training recipe | n/a | Method transfers; the mobile base does not apply to a fixed dual-arm |

LeRobot (the `lerobot` env, 0.6.1) lists ACT, Diffusion, SmolVLA, pi0, pi0.5 and GR00T among supported policies, so one data format (LeRobot datasets) serves all of them. Larger models: rent a cloud GPU for training and run inference locally.

## Order of work

1. **M2/M3 first.** Tracking and organ perception are the foundation any policy sits on, and there are no robot demonstrations yet.
2. **VLM learning (can start now, in `prl-perception`).** Run a small open VLM on strawberry frames to label organs; compare with SAM 2.1 / DINOv3 features. Learn: prompting, LoRA fine-tuning, evaluation on a labelled held-out set.
3. **M5 simulation.** Needs a verified SO-101 model. Collect simulated demonstrations in MuJoCo.
4. **M6 hardware.** Teleoperated demonstrations, then ACT and Diffusion Policy, then SmolVLA. Supervised, with a physical stop.
5. **M7 industrial dual-arm.** Needs its own interface spec and safety procedure before any policy touches it. Policy output never bypasses the guarded-execution layer; a policy cannot override workspace, collision, force or e-stop limits.

## Learning path for VLMs

1. Transformer and attention basics; vision transformers (DINOv3 is one).
2. How a VLM joins a vision encoder to a language model.
3. Inference with a small open VLM; measure accuracy on your own labels.
4. LoRA / quantized fine-tuning on a small dataset.
5. Action heads: how a VLA turns the same backbone into robot actions.

Evidence rule: any accuracy or success-rate claim needs a held-out set, a recorded config and source revision. Do not report numbers from papers as PRL results.
