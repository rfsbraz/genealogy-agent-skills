# Research basis and implementation boundary

Consulted 17 October 2026. These primary sources motivate the design; none validates this four-context agent protocol or establishes that four prompts are statistically independent. The four methods combine palaeographic practice and recognition strategies. This is an engineering design to test, not a claim of benchmarked accuracy.

## A/B: local morphology and writer-specific exemplars

The US National Archives' [Transcription Tips](https://www.archives.gov/citizen-archivist/transcribe/tips) discusses characteristic letter shapes, comparison within a scribe's writing, spelling preservation and uncertain text. We separate local feature inspection from same-hand comparison so each must produce a different, inspectable evidence record. A reports visible shapes; B cites actual examples and mismatches. These are analyses performed by a visual model, not independently trained classifiers. The archive's examples also show contextual interpretation; our protocol keeps that work separately identifiable in D.

## C: complete-line recognition without forced character cuts

Romero et al., [Handwritten Text Recognition for Historical Documents](https://aclanthology.org/W11-4114/), 2011 ([paper](https://aclanthology.org/W11-4114.pdf)), treats historical cursive recognition as a sequence problem, distinguishing image evidence and language modelling. This motivates reading a complete line as a unit rather than assuming reliable character segmentation.

Two concrete modern implementations are relevant:

- [Kraken's API documentation, version 6.0.0](https://kraken.re/6.0.0/tutorials/api.html) describes line segmentation, loading a trained recognition model, and CTC decoding from network output to labels. A real run needs the library, model and an appropriate input/segmentation. Scores are tool outputs, not automatically calibrated truth probabilities.
- Li et al., [TrOCR: Transformer-based Optical Character Recognition with Pre-trained Models](https://arxiv.org/abs/2109.10282), describes an image-transformer/text-transformer recognition architecture. The [Microsoft implementation](https://github.com/microsoft/unilm/tree/master/trocr) provides models/code. A suitable checkpoint and script/language fit must be checked before using it on a historical record; a model's name is not evidence that it suits Portuguese parish handwriting.

This skill does not bundle those dependencies or weights. With a suitable installed/authorized engine, retain its actual raw result and metadata. Otherwise C is explicitly a **whole-line vision-model reading**. Its prompt-level strategy follows the line-recognition idea but does not simulate or implement CTC, a trained HMM, or TrOCR. This preserves four usable methods in a normal vision-enabled agent host without fabricating technology runs.

## D: lexical, grammatical and document constraints

Romero et al. distinguish visual-model evidence from language priors and illustrate document-specific constraints for a historical marriage index. Our contextual method similarly lists constraints and where each comes from. It is qualitative unless an actual decoder is supplied. Period spelling, abbreviation guides and verified locality references may narrow possibilities; open-vocabulary names and contrary strokes must remain possible. A closed lexicon or strong prior can conceal the very rare name being sought, so contextual completions remain separate from literal text.

## What remains to evaluate

Assess transcription accuracy on held-out, human-reviewed manuscript crops, especially rare personal/place names, damaged text, abbreviations and negation. Compare the combined protocol with a simple baseline using character/word error and consequential-field errors; retain abstentions and measure high-confidence mistakes. Test with and without context and same-hand samples. Keep answer keys out of method inputs. A small workflow trial can show method separation and honest uncertainty; it cannot establish improvement or calibrated confidence.
