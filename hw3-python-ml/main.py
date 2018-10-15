#!/usr/bin/env/python3
"""
Created on Sept 15 2018
@author: Kyle Gilde
"""

# Training dataset url: https://www.kaggle.com/c/titanic/download/train.csv
# Scoring dataset url: https://www.kaggle.com/c/titanic/download/test.csv

#### pull_data.py ####
import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import Imputer, StandardScaler
from sklearn.metrics import precision_recall_fscore_support
from sklearn.pipeline import Pipeline
import pickle


# Initiate constants & function
GITHUB_URL = 'https://raw.githubusercontent.com/kylegilde/D622-Machine-Learning/master/titanic-data/'
FILE_NAMES = ['train.csv', 'test.csv?']


def validate_df(df):
    """
    Validates that the object is a dataframe and is not an empty dataframe
    Sources: https://stackoverflow.com/questions/14808945/check-if-variable-is-dataframe
    https://pandas.pydata.org/pandas-docs/version/0.18/generated/pandas.DataFrame.empty.html
    """
    if isinstance(df, pd.DataFrame) and not df.empty:
        print('The dataframe loaded correctly!')
    else:
        print('The dataframe did NOT load correctly!')

# Read csvs
try:
    train_df, test_df = pd.read_csv(GITHUB_URL + FILE_NAMES[0]), pd.read_csv(GITHUB_URL + FILE_NAMES[1])
except Exception as e:
    print(e)
    print('Github file not read')
else:
    # Validate dataframes
    validate_df(train_df)
    validate_df(test_df)

# Create local files
train_df.to_csv('train.csv', index=False)
test_df.to_csv('test.csv', index=False)

print('train.csv & test.csv should now be found in the working directory' )

#### train_model.py ####

try:
    train_df, test_df = pd.read_csv('train.csv'), pd.read_csv('test.csv')
except Exception as e:
    print(e)
    print('Failed to load train and test CSVs')
else:
    # Combine data for munging
    train_rows = train_df.shape[0]
    all_data = pd.concat([train_df, test_df], sort=False)

    # Data Munge
    all_data.Pclass = all_data.Pclass.astype(str) # Pclass should be treated as a categorical variable
    all_data['Deck'] = (all_data.Cabin.str.slice(0, 1) # Create Deck variable
                        .fillna('Unk')) # replace NaNs with 'Unk'
    all_data['Title'] = all_data.Name.str.extract(r'^.*?, (.*?)\..*$') #extract title from name; Source: https://www.kaggle.com/gzw8210/predicting-survival-on-the-titanic
    all_data['Embarked'] = all_data.Embarked.fillna('S') # Replace NaNs with the mode value
    all_data = all_data.drop(['PassengerId', 'Cabin', 'Ticket', 'Name'], axis=1) # drop unneeded variables
    all_data = pd.get_dummies(all_data)

    #figure out which dummy levels to drop
    pd.set_option('display.max_columns', 50)
    all_data.describe(include='all')
    # drop dummy levels
    all_data = all_data.drop(['Pclass_3', 'Sex_female', 'Embarked_S',
                              'Deck_A', 'Title_Mr'], axis=1)

    # split back into training test sets
    train_df, test_df = all_data[ :train_rows], all_data[train_rows: ]
    X_test = test_df.drop('Survived', axis=1)
    # create holdout set to test accuracy
    X, y = train_df.drop('Survived', axis=1), train_df.Survived
    X_train, X_holdout, y_train, y_holdout = train_test_split(X, y, test_size=0.3,
                                                              random_state=42, stratify=y)

    # Create the ML Pipeline
    steps = [('imputation', Imputer(missing_values='NaN', strategy='mean', axis=0)),
             ('scaler', StandardScaler()),
             ('knn', KNeighborsClassifier(n_neighbors=7))]

    # Instantiate pipeline
    pipeline = Pipeline(steps)
    # fit model pipeline
    pipeline.fit(X_train, y_train)

    # Save test & holdout sets
    y_holdout_df = pd.DataFrame()
    y_holdout_df['y_holdout'] = y_holdout
    file_outputs = ['X_test', 'y_holdout_df', 'X_holdout']
    for file_output in file_outputs:
        eval(file_output).to_csv('%s.csv' % file_output, index=False)

    # Pickle model for another day
    model_filename = 'knn_pipeline.pkl'
    with open(model_filename, 'wb') as f: #source: https://stackoverflow.com/questions/10592605/save-classifier-to-disk-in-scikit-learn
        pickle.dump(pipeline, f)

    file_outputs.append(model_filename)
    print('The following files should now be found be in the working directory: ' + ', '.join(file_outputs))
    # Source: https://stackoverflow.com/questions/5618878/how-to-convert-list-to-string

def save_classification_report(class_report, csv_filename):
    """
    Takes the tuple produced by sklearn precision_recall_fscore_support as input
    Creates a dataframa that is the equivalent table generated by sklearn's classification_report
    Writes the dataframa to CSV
    Source: https://stackoverflow.com/questions/39662398/scikit-learn-output-metrics-classification-report-into-csv-tab-delimited-format
    """
    if not isinstance(class_report, tuple):  #source: https://stackoverflow.com/questions/7086990/how-to-know-if-a-variable-is-a-tuple-a-string-or-an-integer
        print('InputError: Please use the tuple from precision_recall_fscore_support')
    elif csv_filename[-4:] != '.csv' or len(csv_filename) < 5:
        print('InputError: Please use a proper CSV filename.')
    else:
        out_dict = {}
        columns = ['precision', 'recall', 'f1_score', 'support']
        zipped = zip(columns, class_report)
        for column, array in zipped: # create dict
            out_dict[column] = array
        out_df = pd.DataFrame(out_dict, index=pipeline.classes_) # cast as df
        avg_tot = (out_df.apply(lambda x: x.mean() if x.name!="support" else  x.sum()).to_frame().T) # get column means
        avg_tot.index = ["avg/total"]
        out_df = out_df.append(avg_tot).round(2)
        out_df.to_csv(csv_filename)

try:
    # Read csvs
    X_test, y_holdout_df, X_holdout = pd.read_csv('X_test.csv'), pd.read_csv('y_holdout_df.csv'), pd.read_csv('X_holdout.csv')
    # Open ML Pipeline
    pipeline = pickle.load(open('knn_pipeline.pkl', 'rb')) #Source: https://stackoverflow.com/questions/18963949/error-pickling-in-python-io-unsupportedoperation-read
except Exception as e:
    print(e)
    print('Failed to load CSVs or model.')
else:
    # test model on holdout dataset
    y_holdout_pred = pipeline.predict(X_holdout)
    # create cassification metrics
    class_report = precision_recall_fscore_support(y_holdout_df.y_holdout, y_holdout_pred)
    # create CSV
    save_classification_report(class_report, 'class_report.csv')
    # predict y for text X
    df = pd.DataFrame()
    df['y_pred'] = pipeline.predict(X_test)
    # write to CSV
    df.y_pred.to_csv('y_pred.csv', index=False)

    print('class_report.csv & y_pred.csv should now be found be in the working directory.')

