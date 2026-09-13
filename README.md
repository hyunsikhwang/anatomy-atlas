# ANATOMY ATLAS

Korean 3D anatomy viewer with skeletal, muscular and organ layers; opacity controls; labels; animated focus; exploded and geometrical cross-section views.

193 selectable structures/regions: 79 parent/standalone structures plus 114 child selections in 20 organ groups. Spine: cervical (7 vertebrae), thoracic (12), lumbar (5), discs (23); pelvic bones: 3 male and 4 female selections (including fused sacra and the source-provided female coccyx); hyoid/laryngeal cartilage: 2; brain: 29 regions; heart: 10; liver: 12; lungs: 7; small intestine: 3; male-reference colon: 7; female colon: 8; eyes: 8; pancreas: 2; uterus: 4; mammary glands: 6; penis: 3. Both eyes, adrenal glands, pituitary, tongue and sex-specific reproductive structures are included. Switch between rotation and screen-plane dragging; right-button drag, two-finger pan/pinch, direction buttons and focused-canvas arrow keys are supported. Arrow buttons/keys move the viewpoint in the indicated direction; drag gestures move the model with the pointer. Home and the frame-all button restore the overview.

## Data and scope

BodyParts3D 4.0, via https://github.com/ashemag/human-atlas, CC BY 4.0. Native BP3D structure coordinates are preserved. One mislabeled right-choroid mesh with out-of-orbit vertices is omitted; right-eye sclera, iris, lens and remaining choroid surfaces are retained.

HRA female v1.5 supplies female reproductive organs, pelvic bones, bladder, colon and developed mammary gland structures. They share one translation into the common frame, preserving their source relationships. Female pelvis/bladder/colon replace the corresponding male structures. This is a composite educational reference, not a female full-body scan: remaining skeleton, muscles and organs use the common BP3D reference. Mammary tissue exists in men too; only developed female lobes/ducts/sinuses are separately represented. No pregnancy structures are included. The two HRA lung surfaces use the previously documented envelope registration. Read public/ATTRIBUTION.md and public/model-scope.json.

## Model audit

Revision 7 removes four redundant BodyParts3D surfaces and the twice-traversed female cervicovaginal junction. Hyoid/laryngeal and named muscle assignments are corrected without moving source geometry. The spine has four selectable regional groups; the native sacrum remains in the sex-specific pelvis assemblies. Public model-audit.json documents source identities, corrections and limits. The available male sacral mesh is not artificially divided to invent a coccyx.

Revision 8 exposes both original sacra as fused S1–S5 selections and the existing HRA female coccyx as a separate selection. The spine links to these same pelvic selections. Male coccyx source availability is explicitly distinguished from biological presence. S1–S5 are not artificially segmented.

## Development

Use the existing pnpm lockfile and Sites scripts. Production build: `pnpm build`.

The authoritative runtime assets are public/models/anatomy-v13.json and the gzip byte segments listed by anatomy-v13-manifest.json. Splitting keeps each static asset below the host limit. Both configurations load once; switching changes visibility and available selections without another model download. Whole-organ selection highlights its child meshes; individual selection reveals only that region in the foreground. In exploded mode, the active organ family also separates its child regions.

extract-sacrum.py upgrades the preceding v7 pack using committed source component metadata in scripts/source-manifests/pelvis.json. It preserves the original pelvic component positions, normals and triangles.

audit-and-classify-anatomy.py upgrades the preceding v6 pack to v7 using the BP3D source files and female-manifest.json (the JSON chunk from the attributed HRA GLB). It checks source duplicate connectivity/coordinates and preserves unaffected geometry byte for byte.

repair-appendix.py upgrades the v5 runtime pack using atlas.json and body-9.bin.gz: native appendix FJ2565 restored; FJ2599 (the source cecum/ileocecal-junction surface) moved from common ileum to male colon. Both sexes have a cecum and appendix selection. Unchanged geometry is checked byte for byte during repacking. To reproduce the migration, use the v5 pack from the preceding repository revision.

subdivide-anatomy.py uses the previous base-v4.json/base-v4.bin snapshot and original source meshes to construct the child asset pack.

Optional preparation scripts expect source downloads in /workspace/scratch/anatomy-assets and are not required for build. extend-sex-anatomy.py expects base-v2-anatomy.json, base-v2-anatomy.bin.gz, atlas.json, body chunk files and female.glb there.

## Validation

`node --experimental-strip-types scripts/verify-anatomy.mjs` checks all 193 mesh buffers and selected-object ray intersections, 3,860 camera fits, 579 local slices, sex-filtered selection and unique replacement structures, eye lateral bounds, and 45 pan projection/distance invariants. It also verifies all 114 child selection/isolation transitions and parent click routing. Bowel regression checks require one appendix and cecum per sex, native right-sided placement, proximity of appendix and cecal reference surfaces, correct source-mesh ownership, and selection visibility with previously hidden layers. Pelvic checks compare all 17 source components with the retained parent arrays, including identical normals and rebased triangle indices. Regression checks also cover spine region counts, source ownership, duplicate aliases and corrected muscle groups. When the HRA manifest is available, all 35 female groups are compared with original accessor bounds and counts, and lung child alignment is checked. When upstream files are available, it compares native coordinates, normals and triangles, and female groups against available source coordinates, and lung children against their already registered parent buffers.

Selection uses a separate depth pass so surrounding anatomy cannot mask small organs. Section mode centers its slicing range on the selected structure. Browser QA and WebMCP runtime validation were not run in this managed session.


## Surface audit and female genital context
`review-anatomy-surfaces.py` upgrades the preceding v8 pack to v11. It removes five redundant mirrored pelvic surfaces and the duplicate pancreatic envelope, retaining original coordinates. It exposes the two existing vaginal components independently. `surface-audit.json` documents the review and limits. The verification script now uses the available `.sites-runtime/anatomy-sources` cache for all BP3D coordinates and HRA accessor bounds/counts, with fallback to the historical cache path.

Selecting a female internal reproductive organ shows its connected tract by default in whole mode. The connected-structure switch, selection zoom and isolated view can narrow the focus. All related surfaces share natural source coordinates and the same foreground depth pass. Explode and section modes disable connection context. Cross sections now clip only supplied surface triangles; synthetic filled caps are removed because they can misrepresent hollow organs and incomplete wall meshes. The model does not reproduce microscopic layers, mucosal folds, or all anatomical variants.

## Educational internal diagrams (revision 12)

Choose **여성 → 도해** to open the vaginal/uterine cutaway, or switch between **질** and **자궁·경부** within the diagram controls. This optional mode adds eight individually selectable tissue bands, an empty continuous schematic lumen, vaginal rugae, adjustable anterior opening width, layer visibility controls and an original-exterior overlay. Clicking a tissue or its label animates the camera to that tissue and shows its function and histology reference. **도해 전체** restores the connected view; **원본 보기** returns to the unchanged source geometry. Sex changes, unsupported organ selections and overview commands leave diagram mode. The viewer's normal layers, pan/orbit, source subdivisions, exploded and geometric section modes remain available.

The source pack remains v11, with all 193 original selections unchanged. `prepare-diagram-profiles.py` derives illustrative convex section envelopes in the registered HRA frame and anchors the cervical channel at the source internal/external os. It writes `public/models/diagram-profiles-v1.json`; no upstream downloads are needed. `app/anatomy-diagram.ts` constructs separate tissue-band surfaces and cut edges, never a disk across the lumen. The profile asset is loaded separately, so a failed diagram download does not prevent the source viewer from opening. Geometry is rebuilt only when cutaway width or rugae changes; animation and camera updates reuse the meshes.

These are teaching diagrams, not recovered histological data. Opened potential spaces, tissue thickness and colors are illustrative; the vaginal/ectocervical connection, fornices and distal cut are simplified. Corpus, cervical and vaginal tissues have distinct labels. Original-exterior overlay and persistent diagram badges make the scope visible. `public/diagram-scope.json` records exact limitations and medical references; the original surface audit remains applicable to the source model.

`node --experimental-strip-types scripts/verify-diagram.mjs` checks 48 generated tissue geometries across opening extremes and rugae states, 36 rays through empty lumina, independent tissue picking, 144 camera fits, source-pack SHA-256, source bounds, three landmark coincidences, nested tissue boundaries, closed fundus, sex gating and transitions back to original anatomy. The existing full anatomy regression and TypeScript check also apply. Offline geometry renders are used for cutaway review; browser QA is not run under the managed execution profile.

## Bilateral lung registration correction (revision 13)

The original separate lung fits used different x/y/z scales. The right reference included FJ2041/FJ2044, whose bounds lie far inferior to the thoracic bronchial trees. That reference produced a 29.34 cm right-lung height versus 20.49 cm on the left. `repair-lung-registration.py` undoes both independent stretches and translates the native HRA lung pair as one unit, using the combined valid BP bronchovascular envelope center as an approximate positioning reference. Native scale, bilateral proportions and relative lobe locations are preserved. The reference right lung is now 20.55 cm high and the left 22.30 cm; the right remains wider and has a larger diagnostic mesh volume. These are model dimensions, not population norms or physiological lung capacities.

Both parents and all seven child selections share the same transform. Triangle indices are unchanged everywhere; the remaining 184 structures are byte-identical to v11. Genital diagram profiles are unchanged, with their pack checksum updated to v13. `public/lung-audit.json` records source bounds, transforms, excluded alignment references, before/after metrics and limits. The anatomy verifier checks all nine lung structures against the original HRA accessor bounds under the shared transform, normal lengths, child alignment, lobe counts and native right/left proportions. This composite registration is educational, not clinically validated.
