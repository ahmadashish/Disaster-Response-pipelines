import pandas as pd
import numpy as np
import os
import pickle
from sqlalchemy import create_engine
import re
import nltk
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier,AdaBoostClassifier
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import make_scorer, accuracy_score, f1_score, fbeta_score, classification_report
from scipy.stats import hmean
from scipy.stats.mstats import gmean
from custom_transformer import StartingVerbExtractor
nltk.download(['punkt', 'wordnet', 'averaged_perceptron_tagger'])
import sys


def load_data(database_filepath):
    cwd = os.getcwd()
    dbwd = cwd.replace('/models','/data/').replace('\\models','\\data\\')
    engine = create_engine('sqlite:///'+ database_filename)
    df = pd.read_sql_table('df', engine)
    X = df['message']
    Y = df.iloc[:,4:]
    category_names = Y.columns

    return X, Y, category_name



def tokenize(text):
    url_regex = 'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    detected_urls =  re.findall(url_regex, text)
    for url in detected_urls:
        text = text.replace(url, "urlplaceholder")
    tokens = word_tokenize(text)
    lemmatizer = WordNetLemmatizer()
    clean_tokens = []
    for tok in tokens:
        clean_tok = lemmatizer.lemmatize(tok).lower().strip()
        clean_tokens.append(clean_tok)

    return clean_token


def build_model():
    pipeline = Pipeline([
        ('features', FeatureUnion([
            ('text_pipeline', Pipeline([
                ('vect', CountVectorizer(tokenizer=tokenize)),
                ('tfidf', TfidfTransformer())
            ])),

            ('starting_verb', StartingVerbExtractor())
        ])),

        ('clf', MultiOutputClassifier(AdaBoostClassifier()))
    ])

    parameters = {
        'features__text_pipeline__vect__ngram_range': ((1, 1), (1, 2)),
        'features__text_pipeline__vect__max_df': (0.5, 0.75, 1.0),
        'features__text_pipeline__vect__max_features': (None, 5000, 10000),
        'features__text_pipeline__tfidf__use_idf': (True, False),

    }


    scorer = make_scorer(multioutput_fscore,greater_is_better = True)

    cv = GridSearchCV(model, param_grid=parameters, scoring = scorer,verbose = 2, n_jobs = -1) ##Then, pass the model and parameter grid to the grid search object.

    return cv


def multioutput_fscore(y_true,y_pred,beta=1):
    score_list = []
    if isinstance(y_pred, pd.DataFrame) == True:
        y_pred = y_pred.values
    if isinstance(y_true, pd.DataFrame) == True:
        y_true = y_true.values
    for column in range(0,y_true.shape[1]):
        score = fbeta_score(y_true[:,column],y_pred[:,column],beta,average='weighted')
        score_list.append(score)
    f1score_numpy = np.asarray(score_list)
    f1score_numpy = f1score_numpy[f1score_numpy<1]
    f1score = gmean(f1score_numpy)

    return  f1score

def evaluate_model(model, X_test, Y_test, category_names):
    model = build_model()
    y_pred = model.predict(X_test)
    multi_f1 = multioutput_fscore(y_test,y_pred, beta = 1)
    overall_accuracy = (y_pred == y_test).mean().mean()
    print('Average overall accuracy {0:.2f}% \n'.format(overall_accuracy*100))
    print('F1 score (custom definition) {0:.2f}%\n'.format(multi_f1*100))
    y_pred_pd = pd.DataFrame(y_pred, columns = y_test.columns)
    for column in y_test.columns:
        print('------------------------------------------------------\n')
        print('FEATURE: {}\n'.format(column))
        print(classification_report(y_test[column],y_pred_pd[column]))

    pass


def save_model(model, model_filepath):
    filename = model_filepath
    pickle.dump(model, open(filename, 'wb'))
    pass


def main():
    if len(sys.argv) == 3:
        database_filepath, model_filepath = sys.argv[1:]
        print('Loading data...\n    DATABASE: {}'.format(database_filepath))
        X, Y, category_names = load_data(database_filepath)
        X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2)

        print('Building model...')
        model = build_model()

        print('Training model...')
        model.fit(X_train, Y_train)

        print('Evaluating model...')
        evaluate_model(model, X_test, Y_test, category_names)

        print('Saving model...\n    MODEL: {}'.format(model_filepath))
        save_model(model, model_filepath)

        print('Trained model saved!')

    else:
        print('Please provide the filepath of the disaster messages database '\
              'as the first argument and the filepath of the pickle file to '\
              'save the model to as the second argument. \n\nExample: python '\
              'train_classifier.py ../data/DisasterResponse.db classifier.pkl')


if __name__ == '__main__':
    main()
