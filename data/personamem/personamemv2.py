# ----------------------------------
# Python script that takes the sample of the PersonaMemV2 dataset
# and returns a smaller subset of itself with the respective contents
# to test the accuracy
# ----------------------------------

import pandas as pd

splits = {'benchmark_multimodal': 'benchmark/multimodal/benchmark.csv', 'train_multimodal': 'benchmark/multimodal/train.csv', 'val_multimodal': 'benchmark/multimodal/val.csv', 'benchmark_text': 'benchmark/text/benchmark.csv', 'train_text': 'benchmark/text/train.csv', 'val_text': 'benchmark/text/val.csv'}
df = pd.read_csv("hf://datasets/bowen-upenn/PersonaMem-v2/" + splits["benchmark_multimodal"])