Understanding Neural Scaling Laws
Abstract
Neural scaling laws describe how model performance improves predictably as a function of compute, data, and parameter count.¹ These power-law relationships have been empirically validated across a wide range of architectures and tasks.² This paper reviews the key findings and their practical implications for resource allocation in large-scale training runs.³
1. Introduction
The observation that loss decreases as a smooth power law of scale was first systematically documented in
Kaplan et al. (2020).n Subsequent work confirmed that the optimal compute allocation shifts toward larger models and less data as total compute increases.n This result, known as the Chinchilla scaling law,n overturned conventional wisdom that had favoured large models trained on relatively small datasets.
2. Methodology
We replicate the core scaling experiments using a decoder-only transformer architecture.n Models range from
1M to 1B parameters. Training data is drawn from a deduplicated web corpus filtered with a quality classifier.n
All runs use the same tokenizer with a vocabulary of 32,768 tokens.n
Footnotes
¹ Hestness et al., 2017. Deep Learning Scaling is Predictable, Empirically.
² Zoph et al., 2022. ST-MoE: Designing Stable and Transferable Sparse Expert Models.
³ Hoffmann et al., 2022. Training Compute-Optimal Large Language Models.
n Kaplan et al., 2020. Scaling Laws for Neural Language Models.
n Compute-optimal training implies fewer tokens per parameter than previously assumed.
n Named after the Chinchilla model; trained on 4× more tokens than GPT-3 at equal FLOPs.
n Vaswani et al., 2017. Attention Is All You Need.
n Quality filtering reduces noise and improves downstream task performance.
n Byte-pair encoding with a coverage-optimised merge schedule.
