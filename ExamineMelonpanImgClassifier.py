# coding: utf-8
from mlsp.ml.CNNClassifierStaticObject import CNNClassifierStaticObject
import cv2
import numpy as np
import os


def main():
    clsfr = CNNClassifierStaticObject()
    train_data_base = 'train_data'
    clsfr.train_data_dir = os.path.join(train_data_base, 'melonpan')
    clsfr.intermediate_data_dir = os.path.join(train_data_base, 'features')
    clsfr.weight_dir = os.path.join(train_data_base, 'weight')
    clsfr.log_data_dir = os.path.join(train_data_base, 'log')
    clsfr.identifier = 'melonpan'
    clsfr.classes = ['melonpan', 'guild_battle', 'others']
    clsfr.dense_shape = [192, 96]

    samples = [
        cv2.imread(os.path.join(train_data_base, 'melonpan_verify', 'melonpan_0802.jpeg')),
        cv2.imread(os.path.join(clsfr.train_data_dir, 'sub_melonpan', 'melonpan_0735.jpeg')),
        cv2.imread(os.path.join(train_data_base, 'melonpan_verify', 'スクリーンショット 2018-01-09 21.41.10.png')),
        cv2.imread(os.path.join(train_data_base, 'melonpan_verify', 'IMG_2165.JPG')),
        ]
    samples = clsfr.sample_image(samples, resized_shape=(clsfr.input_x, clsfr.input_y), normalization=True)

    if clsfr.run_train():
        clsfr.prepare_classify()
        y, predictions = clsfr.classify(np.array(samples))
        print(y)
        print(predictions)


if __name__ == '__main__':
    main()

"""
3classes(melonpan, guild_battle, others)
ベリファイメロンパンvs怪しいメロンパンvsギルバトvsその他（俺の顔）
top_denseのcomparison
/256-128
    - mean_absolute_error: 0.0102 
    - categorical_accuracy: 0.9901 
    - val_loss: 0.0272 
    - val_mean_absolute_error: 0.0080 
    - val_categorical_accuracy: 0.9921
    ['melonpan', 'melonpan', 'guild_battle', 'others']
    [[1.0000000e+00 5.7420525e-25 1.3735165e-13]
     [9.9999750e-01 6.9406672e-12 2.5083507e-06]
     [3.3034496e-02 9.6536660e-01 1.5988977e-03]
     [4.2890722e-01 5.1664833e-06 5.7108766e-01]]
/256-64
     - mean_absolute_error: 0.0059 
     - categorical_accuracy: 0.9941 
     - val_loss: 0.0187 
     - val_mean_absolute_error: 0.0053 
     - val_categorical_accuracy: 0.9953
    ['melonpan', 'melonpan', 'guild_battle', 'others']
    [[1.0000000e+00 2.4694369e-18 2.3377734e-12]
     [9.9999952e-01 1.6657176e-10 4.2271665e-07]
     [6.8176934e-07 9.9999774e-01 1.6051611e-06]
     [9.3843691e-02 2.8853583e-07 9.0615600e-01]]
/192-96 => 採用
    - mean_absolute_error: 0.0093 
    - categorical_accuracy: 0.9881 
    - val_loss: 0.0158 
    - val_mean_absolute_error: 0.0058 
    - val_categorical_accuracy: 0.9921
    ['melonpan', 'melonpan', 'guild_battle', 'others']
    [[1.0000000e+00 1.6470960e-19 7.1431897e-12]
     [9.9998736e-01 2.6693228e-09 1.2684744e-05]
     [1.0016815e-05 9.9820530e-01 1.7847304e-03]
     [1.5164448e-02 3.1647721e-06 9.8483235e-01]]
/192-64
    - mean_absolute_error: 0.0097 
    - categorical_accuracy: 0.9901 
    - val_loss: 0.0487 
    - val_mean_absolute_error: 0.0098 
    - val_categorical_accuracy: 0.9858
    ['melonpan', 'melonpan', 'guild_battle', 'melonpan']
    [[1.0000000e+00 8.9838267e-17 7.1149406e-14]
     [9.9999571e-01 2.4031522e-07 4.0197988e-06]
     [2.5725896e-07 9.9999893e-01 8.1436048e-07]
     [7.0735919e-01 5.1547573e-05 2.9258931e-01]]
/128-128
    - mean_absolute_error: 0.0104
    - categorical_accuracy: 0.9901 
    - val_loss: 0.0234 
    - val_mean_absolute_error: 0.0073 
    - val_categorical_accuracy: 0.9889
    ['melonpan', 'melonpan', 'guild_battle', 'others']
    [[1.0000000e+00 7.8777385e-23 2.0003188e-10]
     [9.9998713e-01 3.8305123e-12 1.2872302e-05]
     [1.8380719e-03 9.0530640e-01 9.2855468e-02]
     [1.8252900e-02 7.7617642e-06 9.8173928e-01]]
/128-96
     - mean_absolute_error: 0.0149 
     - categorical_accuracy: 0.9869 
     - val_loss: 0.0365 
     - val_mean_absolute_error: 0.0097 
     - val_categorical_accuracy: 0.9842
    ['melonpan', 'melonpan', 'guild_battle', 'others']
    [[1.0000000e+00 1.2414359e-11 6.5307342e-09]
     [9.9935406e-01 8.7926873e-07 6.4506929e-04]
     [2.3057932e-04 8.0668324e-01 1.9308612e-01]
     [1.7566477e-04 3.9151010e-07 9.9982399e-01]]
/128-64
     - mean_absolute_error: 0.0089 
     - categorical_accuracy: 0.9885 
     - val_loss: 0.0132 
     - val_mean_absolute_error: 0.0056 
     - val_categorical_accuracy: 0.9937
    ['melonpan', 'melonpan', 'guild_battle', 'others']
    [[1.0000000e+00 1.1061944e-22 4.8105109e-10]
     [9.9954742e-01 4.6250048e-09 4.5252522e-04]
     [1.9183306e-03 9.7055411e-01 2.7527584e-02]
     [2.7230557e-02 1.5847767e-05 9.7275364e-01]]
/64-64
     - mean_absolute_error: 0.0203 
     - categorical_accuracy: 0.9739 
     - val_loss: 0.0293 
     - val_mean_absolute_error: 0.0086 
     - val_categorical_accuracy: 0.9873
    ['melonpan', 'melonpan', 'guild_battle', 'others']
    [[9.99999881e-01 3.19124361e-17 1.12989298e-07]
     [9.99583423e-01 3.92398514e-09 4.16599942e-04]
     [1.32804345e-02 9.56170380e-01 3.05492096e-02]
     [3.87346838e-03 1.78466085e-03 9.94341850e-01]]
     
2c(melonpan, others)
ベリファイメロンパンvs怪しいメロンパンvsギルバトvsその他（俺の顔）
top_denseのcomparison
/256-128
     - mean_absolute_error: 0.0118
     - categorical_accuracy: 0.9930
     - val_loss: 0.0788
     - val_mean_absolute_error: 0.0241
     - val_categorical_accuracy: 0.9742
     ['melonpan', 'melonpan', 'others', 'others']
    [[1.0000000e+00 2.7515693e-10]
     [9.9998248e-01 1.7570643e-05]
     [1.3416062e-02 9.8658401e-01]
     [2.3897983e-02 9.7610199e-01]]
/128-128
     - mean_absolute_error: 0.0279
     - categorical_accuracy: 0.9800
     - val_loss: 0.1056
     - val_mean_absolute_error: 0.0245
     - val_categorical_accuracy: 0.9766
    ['melonpan', 'melonpan', 'others', 'others']
    [[1.0000000e+00 8.7223145e-10]
     [9.9985707e-01 1.4289696e-04]
     [1.1479719e-07 9.9999988e-01]
     [3.9668428e-04 9.9960333e-01]]
/128-64
    - mean_absolute_error: 0.0115
    - categorical_accuracy: 0.9924
    - val_loss: 0.0826
    - val_mean_absolute_error: 0.0259
    - val_categorical_accuracy: 0.9719
    ['melonpan', 'melonpan', 'others', 'others']
    [[1.0000000e+00 6.9745618e-09]
     [9.9998081e-01 1.9136598e-05]
     [3.0858375e-03 9.9691415e-01]
     [1.1719031e-02 9.8828095e-01]]
"""