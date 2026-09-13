# Anatomy data attribution

BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International.

- License: https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html (updated 2025-02-27)
- Dataset: https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html
- License terms: https://creativecommons.org/licenses/by/4.0/
- Source geometry: `isa_BP3D_4.0_obj_99.zip`, BodyParts3D 4.0.
- English names and relationships: IS-A and PART-OF concept, element, and inclusion tables from the same archive.
- Publication: Mitsuhashi et al. (2009), BodyParts3D: 3D structure database for anatomical concepts. https://doi.org/10.1093/nar/gkn613

Adaptations: axes and units converted from millimeters/Z-up to meters/Y-up; translated to rest at the stage; geometry simplified using meshoptimizer with 0.2% relative error limit per structure; normals quantized to signed 16-bit; packed into binary chunks; curated display system groupings and colors. The source contains 2,234 individual OBJ meshes; all remain represented. The combined hierarchy contains 3,432 named FMA concepts, which may reference multiple meshes. Original source identity is preserved in the manifest.

Source OBJ comments mention an older CC BY-SA 2.1 Japan license. The official current database license linked above supersedes that legacy text and explicitly permits redistribution and adaptation under CC BY 4.0.

BodyParts3D represents an adult male reference anatomy based on TARO MRI and anatomical illustration refinements. It is not a complete model of every possible human anatomical structure or variation. This interface is educational and is not a clinical tool.

## Historical assets (not included in the current release)

Earlier repository revisions included female reference anatomy: Kristen Browne and Heidi Schlehlein, Human Reference Atlas / HuBMAP, *3D Reference Organ Set for Female v1.5* (2023). CC BY 4.0. Geometry adapted for this viewer.

- Source DOI: https://doi.org/10.48539/HBM352.BTSQ.586
- Dataset: https://lod.humanatlas.io/ref-organ/united-female/v1.5
- Original GLB: https://cdn.humanatlas.io/digital-objects/ref-organ/united-female/v1.5/assets/3d-vh-f-united.glb
- License: https://creativecommons.org/licenses/by/4.0/

Adaptations: translated native meter/Y-up coordinates onto the stage, coincident vertices welded and source normals averaged, geometry simplified with a 0.2% per-structure relative error bound, and normals quantized. Colors and display systems are curated for this interface. All 888 source meshes are represented, with 1,073 source nodes available as selectable individual or compound concepts.

This is a reference assembly with whole-body surface and selected organs, including female reproductive anatomy. Its skeleton and muscle coverage is partial. It is not a complete model of every human structure or a single-person scan. Eight placenta/umbilical structures are classified under Pregnancy reference and hidden by default.

## This viewer
Selected BodyParts3D structures regrouped into Korean anatomical regions; geometry translated to local group centers, colors adapted, layer opacity, organ separation and geometric clipping added. Upstream display classifications were adjusted for selected muscle meshes. No claim of clinical validation.

## Lung surfaces included in this viewer
Kristen Browne and Heidi Schlehlein, Human Reference Atlas / HuBMAP, 3D Reference Organ Set for Female v1.5 (2023), CC BY 4.0.
https://doi.org/10.48539/HBM352.BTSQ.586
https://lod.humanatlas.io/ref-organ/united-female/v1.5
https://creativecommons.org/licenses/by/4.0/
Initial alignment, superseded in revision 13: lung bronchopulmonary segment surfaces were extracted from the united-female GLB, scaled per axis and aligned to BodyParts3D lung-region envelopes. The current shared translation and restored native bilateral proportions are described below. This is a composite reference assembly, not a single-person scan or a clinically validated registration. The historical-assets paragraph above describes the upstream human-atlas project; this viewer includes these adapted lung surfaces.

## Sex-specific organ configurations (viewer revision 3)
BodyParts3D male eye, adrenal, pituitary, tongue and male reproductive meshes are added in their original coordinates. Eye display uses sclera, iris, choroid and lens surfaces; transparent chamber volumes are omitted. The mislabeled FJ1337 right-choroid mesh has out-of-orbit vertices and is excluded; the remaining right-eye surfaces retain their original coordinates. Developed mammary gland display includes lobes, ducts and sinuses; surrounding skin and fat are omitted.
HRA united-female v1.5 reproductive structures, pelvic bones, bladder, colon and developed mammary glands are adapted by a single uniform transform into the common frame. Pelvic internal spatial relationships are preserved. The common skeleton, muscles and remaining organs are teaching references based on the male BodyParts3D model; they are not relabelled as a full female scan. Female pelvic bones replace the male pelvis. Mammary tissue exists in men as well; only the developed female reference is separately represented here. Placenta and umbilical structures are excluded from the non-pregnant configuration.
HRA: Kristen Browne and Heidi Schlehlein; https://doi.org/10.48539/HBM352.BTSQ.586 ; CC BY 4.0.

## Named substructures (viewer revision 5)
97 child selections in 15 organ groups are extracted from named source meshes. Parent organs remain selectable aggregates; only leaf geometry is drawn, preventing parent/child overlap. Native BodyParts3D coordinates are preserved. Existing brain components are supplemented with the source thalami, amygdalae and corpus callosum. Cortical regions regroup the supplied named gyri and do not claim complete cortical parcellation. Ventricular selections are labelled as cavity/papillary-muscle references, not ventricular wall models. No invented geometric segmentation boundaries are used.
HRA lung child surfaces reuse the identical registration of their parent lungs. HRA female colon, uterus and mammary substructures preserve the previously declared female assembly transform. Public substructure-scope.json records group counts and model scope. Functional labels refer to the linked OpenStax Anatomy & Physiology 2e chapters.

## Appendix and cecal grouping correction (viewer revision 6)
The previous male colon group omitted the available native appendix. BodyParts3D FJ2565 (FMA14542, appendix) is now included in the male colon and independently selectable, with every source vertex retained in its original coordinates. No artificial tube, position adjustment or female-to-male geometry transfer is used.
The upstream cecum concept FMA14541 resolves to FJ2599, named “Ileocecal junction” in the element table. That existing surface is reassigned from the shared ileum to the male colon and labelled as a cecal/ileocecal-junction reference; no invented cecal segmentation boundary is introduced. This also removes the duplicated male junction from the female configuration. HRA female appendix node 490 and cecum node 493 retain their existing geometry and assembly transform. Both sex configurations contain one appendix and one cecum selection; their reference shapes and orientations do not imply a sex-specific presence difference.
The packed source is https://github.com/ashemag/human-atlas/blob/main/public/models/atlas.json and body-9.bin.gz in that directory, under the BodyParts3D attribution above. Public substructure-scope.json records the source chunk checksum. Revision 6 contains 178 selectable structures, including 99 children in 15 organ groups.

## Model audit and vertebral regions (viewer revision 7)
The 24 supplied presacral vertebrae are divided into 7 cervical (C1–C7, including atlas and axis), 12 thoracic (T1–T12) and 5 lumbar (L1–L5) vertebrae. All 23 supplied intervertebral discs remain separately selectable as a group. Their original named mesh boundaries and coordinates are preserved. The sacrum remains in the sex-specific pelvis assemblies; a separate male coccyx surface is not fabricated from the available sacral mesh. The HRA female pelvis already includes its native coccyx.

Four redundant BodyParts3D surfaces are removed: FJ2772 duplicates hyoid FJ3201; FJ2440 duplicates cricoid cartilage FJ2769; FJ2386 duplicates hepatic artery branch FJ1916; FJ1450 repeats external anal sphincter FJ2548 within source rounding (maximum coordinate difference 1.014 micrometers, identical triangle indices). The first three pairs are byte-identical in position and index arrays. In the female vaginal assembly, HRA node 432 had been traversed twice, as both a descendant of node 431 and an explicit root; it now appears once, retaining the unique source geometry.

103 regional assignments are corrected without moving any anatomical surface. Hyoid and cuneiform laryngeal cartilages move from the skull to the neck. Intrinsic hand muscles move from forearm groups to hand groups; named shoulder, gluteal, cervical and back muscles are regrouped by anatomy instead of their center height. FJ1469/FJ1469M have reversed upstream thumb-muscle side names; physical laterality and native coordinates are retained. Thigh group labels acknowledge the included iliotibial connective tissue. Hyoid and laryngeal cartilages also become independent selections.

Public model-audit.json records the corrections, source identifiers and audit limits. Current display: 184 selectable structures, with 105 children in 17 groups. This is a source-based educational audit, not clinical anatomical certification or a complete inventory of human anatomy. Functional and regional labels refer to OpenStax Anatomy & Physiology 2e chapters 7.2, 7.3, 11.3, 11.5 and 11.6.

The whole-brain aggregate inventory is synchronized with the five source components already present in its child selections (thalami, amygdalae and corpus callosum). Existing child geometry is unchanged.

## Sacrum and coccyx navigation (viewer revision 8)
Both native sacral surfaces are independently selectable as “천골 · S1–S5”: BodyParts3D FJ3393 for the male configuration and HRA united-female node 963 for the female configuration. S1–S5 designate sacral vertebrae, not coccygeal vertebrae. The supplied adult surfaces are fused sacra; no synthetic S1–S5 segmentation planes or individual sacral vertebral surfaces are introduced.

The female coccyx (HRA node 964) is independently selectable. The male source does not supply a separate coccyx element; the interface explicitly distinguishes this model-data limitation from biological presence in both sexes. No female coccyx is transplanted into the male model. The two hip bones and sacral/coccygeal surfaces are extracted using the original component counts and index boundaries. Every parent surface is preserved once, with unchanged source coordinates, normals and triangle connectivity. Parent pelvic aggregates remain selectable and their duplicate rendering is suppressed by the existing leaf-rendering rule.

The spine list and detail panel link to the same sacrum/coccyx selections in the pelvic hierarchy, without adding duplicate meshes. Committed scripts/source-manifests/pelvis.json records the original source metadata, hashes and packed BP3D bounds; the latter differ slightly from upstream pre-simplification bounds. Reference: https://openstax.org/books/anatomy-and-physiology-2e/pages/7-3-the-vertebral-column . Current display: 191 selectable structures, with 112 children in 19 groups.


## Surface and representation audit (viewer revision 11)
The attached educational image is an opened view of the female genital tract. The viewer retains the native HRA external vaginal envelope: it does not claim to reconstruct its mucosal rugae or tissue layers. Existing nodes 431 and 432 become two child selections, with byte-preserved parent coordinates and triangle connectivity. A connected-structure view includes the native uterus, cervix, uterine tubes and ovaries. Native angulation and relative positions are retained, with no reshaping to imitate a straightened illustration.

Five older mirrored left pelvic representations are removed in favor of their native counterparts: FJ1449M→FJ2542 (coccygeus), FJ1450M→FJ2543 (anal sphincter portion), FJ1453M→FJ2544 (iliococcygeus), FJ1457M→FJ2545 (pubococcygeus), FJ1458M→FJ2546 (puborectalis). Each pair has the same upstream FMA identity and 98.5–99.5% bounding-box intersection-over-union. These are overlapping alternate representations, not byte-identical aliases. The whole-pancreas envelope FJ1895 is removed from the detailed assembly; FJ2629 provides the parenchymal exterior, and the supplied duct components remain. Retained anatomy is not moved or distorted.

The renderer clips only the supplied surface triangles. Automatic solid stencil caps are removed globally: exterior envelopes and cavity casts do not encode organ wall thickness, mucosal layers, or complete interior tissue. A clipped surface is not CT/MRI or a histological section. Labels distinguish the ventricular fluid spaces and the heart model's missing ventricular walls. The liver duct group is labelled “간 담관” to avoid asserting that all represented ducts are intrahepatic.

public/surface-audit.json records the source-based corrections and review limits. This is an educational composite, not a clinical certification of every upstream segmentation. Sources and licenses remain BodyParts3D/human-atlas and HRA united-female v1.5, CC BY 4.0, as attributed above.
Medical references: https://training.seer.cancer.gov/anatomy/reproductive/female/tract.html and https://my.clevelandclinic.org/health/body/22469-vagina .

## Optional internal cutaway diagrams (viewer revision 12)

The existing 193 source structures and the v11 binary pack remain unchanged. An optional female genital cutaway adds eight illustrative tissue selections: vaginal mucosa/rugae, muscle and adventitia; corpus endometrium, myometrium and perimetrium; cervical mucosa and connective-tissue stroma. These procedural teaching geometries are separate from the original HRA surfaces. Their profiles approximate convex envelopes of source cross-sections and keep the existing world registration and uterine inclination. The supplied internal/external cervical-os landmarks anchor the schematic channel. The original outer surfaces may be overlaid and are restored on leaving diagram mode.

The inner contours, opened potential lumina, relative wall thicknesses, colors, mucosal collar and rugae are educational illustrations, not source-derived tissue segmentations or clinically measured anatomy. The upper vaginal/ectocervical transition and distal cut rim are simplified. Fornices, epithelial transformation zone, introitus/vulva, tissue microanatomy and menstrual-phase variations are not reconstructed. Corpus tissue names do not extend into the separately classified cervix or vagina. Other organs retain their source-only surface clipping. Full scope: `/diagram-scope.json`.

Anatomical organization is based on NCI SEER and histological teaching material; no source photographs, illustrations or slide pixels are copied:
- NCI SEER, Genital Tract: https://training.seer.cancer.gov/anatomy/reproductive/female/tract.html
- T. Clark Brelje and Robert L. Sorenson, Histology Guide, MH 173 Vagina: https://histologyguide.com/slideview/MH-173-vagina/18-slide-1.html
- T. Clark Brelje and Robert L. Sorenson, Histology Guide, MHS 207 Cervix: https://histologyguide.com/slideview/MHS-207-cervix/18-slide-1.html
- University of Leeds, Histology Guide, Uterus: https://histology.leeds.ac.uk/home/female/uterus/

HRA source geometry attribution and CC BY 4.0 adaptation terms above also apply to these derived envelope profiles.

## Bilateral lung proportions (viewer revision 13)

The independent axis stretches applied in the initial lung adaptation are removed. The old right alignment envelope included FJ2041 and FJ2044 far below the thoracic bronchial geometry, resulting in an enlarged and inferiorly shifted right lung. These two meshes are excluded from alignment references without assigning them a new biological identity. Both HRA lungs and their seven selectable components now retain native source scale and share a single translation to the combined valid BP bronchovascular envelope center. Original HRA relative proportions and positions are recovered within previous floating-point and normal quantization precision. No target clinical volume ratio is imposed, and no side is mirrored from the other.

All triangle indices and all 184 non-lung structures are unchanged. The source remains the attributed HRA united-female v1.5, CC BY 4.0, in the composite BP3D body. `lung-audit.json` records source identities, the exact translation, before/after mesh dimensions, and review limits. Normal right/left differences are described by NIH NHLBI (right three lobes, left two, heart space on the left) and Cleveland Clinic (right shorter and wider): https://www.nhlbi.nih.gov/health/lungs/respiratory-system and https://my.clevelandclinic.org/health/body/8960-lungs .
