# Isolated real-engine UI maintenance fixture

Used only when maintaining the shared UI parts. It does not become a game build, game acceptance step, native-host test, or physical-device result. The fixture directly runs the real Cocos Creator 2.4 browser engine bundle and shared components with synthetic nodes/art; it reads no game project.

Prepare into a new directory outside the input trees:

```sh
python3 -B tests/real-engine-ui/prepare_ui_engine_fixture.py --engine-bundle /path/to/Creator/engine/bin/cocos2d-js-for-preview.js --candidate-kit /path/to/platform-kit --baseline-kit /path/to/older/platform-kit --out /new/output/path
```

The command copies the supplied engine only into the external output directory; the engine is not distributed in this Skill. It writes input SHA-256s and refuses an existing output or an output inside source trees. It never starts a server, browser, or game. Serve the external directory through the maintenance task's local service and use its own official Ego TaskSpace. `?mode=before` requires an explicit baseline; the default is the candidate (`?mode=after`). Read `window.fixtureResult` after completion. The preserved fixture tests three text overflow modes, state-swapped pictures, Claim production semantics, authored button colour/opacity and late parent layout cover. The file can show deliberately failed results on the old implementation.

Dispose the maintenance space and exact service when finished. Report the exact engine version, bytes and candidate input identities; do not generalize browser component behavior to native SDK, 3.x runtime, art style, or device acceptance. The ordinary Node tests additionally cover watcher cleanup and source glyph metadata.
