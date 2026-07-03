"""TensorFlow/Keras — 함수형 API(tf.keras.Model)로 모델 구성.
Sequential보다 유연한 구조를 짤 때 쓰는 형태 (다중입력/분기 등).
"""
import tensorflow as tf

def build_model(input_dim=10, n_class=2):
    inputs = tf.keras.Input(shape=(input_dim,))
    x = tf.keras.layers.Dense(32, activation="relu")(inputs)
    x = tf.keras.layers.Dropout(0.2)(x)
    x = tf.keras.layers.Dense(16, activation="relu")(x)
    outputs = tf.keras.layers.Dense(n_class, activation="softmax")(x)
    return tf.keras.Model(inputs, outputs)

def main():
    import numpy as np
    x = np.random.rand(300, 10).astype("float32")
    y = np.random.randint(0, 2, 300)

    model = build_model()
    model.compile(optimizer="adam",
                  loss="sparse_categorical_crossentropy",
                  metrics=["accuracy"])
    model.fit(x, y, epochs=3, batch_size=32, verbose=1)

    model.save("functional_model.keras")
    print("saved: functional_model.keras")

if __name__ == "__main__":
    main()
