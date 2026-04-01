import mlflow
import mlflow.sklearn
from sklearn.linear_model import LinearRegression
from sklearn.datasets import make_regression

mlflow.set_tracking_url("http://localhost:3000")
mlflow.set_experiment("meu_experimento_1")

with mlflow.start_run():
    X, y = make_regression(n_samples=100, n_features=1, noise=0.1)
    model = LinearRegression()
    model.fit(X, y)

    mlflow.log_param("coeficiente", model.coef_[0])
    mlflow.log_metric("score", model.score(X, y))
    mlflow.sklearn.log_model(model, "modelo")

    print(f"Modelo salvo no MLflow: {mlflow.get_artifact_url()}")
