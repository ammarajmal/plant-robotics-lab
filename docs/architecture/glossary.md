# Glossary

- **Organ:** Botanical component such as leaf blade, petiole, runner/stolon, flower, or fruit.
- **Candidate:** Unconfirmed potential removal or harvest target.
- **Target:** Selected physical organ or grasp region with an identity within an experiment.
- **Target ID:** Stable session-scoped identifier for that physical target.
- **Observation:** Per-camera measurement at a defined frame and timestamp provenance.
- **Mask:** Pixel-level image region; a per-camera mask ID is not physical identity.
- **Grasp region:** Suitable physical neighborhood on organ.
- **Grasp pose:** Robot-frame 6D position and orientation proposal.
- **LOST:** Physical identity or target location insufficiently trustworthy.
- **False valid:** Tracker presents an incorrect prediction as a valid target.
- **Experiment run:** Frozen code, config, dataset, evaluation and environment provenance.
- **Nominal frame index:** Deterministic playback position derived from decoder
  frame index and reported FPS.
- **Exposure synchronization:** Physical agreement of camera exposure times;
  PRL-003 records this as `unverified`.
- **Playback provenance:** Grounded source, decoder, runtime, configuration,
  output, and execution metadata. Missing values remain `null` or `unknown`.
