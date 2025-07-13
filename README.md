# AI-Driven Maintenance

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/ai-driven-maintenance.git
   ```
2. Navigate to the project directory:
   ```
   cd ai-driven-maintenance
   ```
3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Run the main script:
   ```
   python AI_Driven_Maintenance.py
   ```
2. The script will load the `manufacturing_6G_dataset.csv` file and perform various data analysis and visualization tasks.
3. After the analysis, the script will train and evaluate several machine learning models to predict the Efficiency_Status of the manufacturing process.
4. The results of the model evaluation will be displayed, and the confusion matrices for each model will be plotted.

## API

The main functions and classes used in the project are:

- `train_test_split`: Splits the dataset into training and testing sets.
- `StandardScaler`: Scales the input features to have zero mean and unit variance.
- `RandomForestClassifier`: A tree-based ensemble learning algorithm used for classification.
- `GradientBoostingClassifier`: A tree-based ensemble learning algorithm that uses gradient boosting.
- `LogisticRegression`: A linear model used for binary classification.
- `KNeighborsClassifier`: A k-nearest neighbors algorithm used for classification.
- `SVC`: A support vector machine classifier.
- `DecisionTreeClassifier`: A tree-based algorithm used for classification.
- `GaussianNB`: A Gaussian Naive Bayes classifier.
- `xgb.XGBClassifier`: The XGBoost classifier.
- `lgb.LGBMClassifier`: The LightGBM classifier.
- `cb.CatBoostClassifier`: The CatBoost classifier.

## Contributing

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make the necessary changes and commit them.
4. Push your changes to your forked repository.
5. Submit a pull request to the original repository.

## License

This project is licensed under the [MIT License](LICENSE).

## Testing

To run the tests, execute the following command:

```
python -m unittest discover tests
```

This will run all the tests located in the `tests` directory.
