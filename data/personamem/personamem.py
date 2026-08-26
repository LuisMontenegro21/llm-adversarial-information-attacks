# ----------------------------------
# Python script that takes the sample of the PersonaMem dataset
# and returns a smaller subset of itself with the respective contents
# to test the accuracy
# ----------------------------------

import pandas as pd

splits = {'32k': 'questions_32k.csv', '128k': 'questions_128k.csv', '1M': 'questions_1M.csv'}
df = pd.read_csv("hf://datasets/bowen-upenn/PersonaMem-v1/" + splits["32k"])