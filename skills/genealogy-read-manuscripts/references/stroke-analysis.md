# Assignment A: local stroke and grapheme analysis

Use a bottom-up, feature-based palaeographic method. Work only from the supplied local target images and script metadata. Do not decide words using syntax, familiar names, place lists, document formulas or guessed biographies. Neighbouring letters are visual context only.

1. Establish baseline, relative height and plausible grapheme boundaries, retaining competing segmentations for ligatures or joined letters.
2. Record visible bowls, loops, ascenders, descenders, minim groups, dots, crossbars and entry/exit strokes. Static ink does not prove pen direction or pen-lift timing; label those inferences if relevant.
3. Build candidate character sequences from those features. Mark unresolved internal characters and diacritics. Record a visible feature that would discriminate each consequential alternative, including when it is absent or obscured.
4. Return literal candidates and a `method_product.feature_inventory`: target subregion, observed feature, compatible characters, incompatible characters, and unresolved boundary/mark. Short sequences such as `M[a/o]r…` are preferable to an unsupported whole word.

Set `execution_kind: visual_feature_analysis`. Do not claim a trained character classifier or computed image features unless a real tool actually produced them. The goal is an auditable local visual constraint, not grammatical completion.
