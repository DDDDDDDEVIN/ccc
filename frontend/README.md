"# Frontend Notebook" 
Please follow the steps below in your Anaconda Navigator terminal (or any terminal with conda):

conda create -n sentiment-map python=3.10 -y
conda activate sentiment-map

conda install -c conda-forge geopandas -y
conda install -c conda-forge ipywidgets -y

pip install plotly
pip install wordcloud

jupyter notebook

Don't close the terminal and then run.ipynb

If ipywidgets doesn't render correctly, run:
jupyter nbextension enable --py widgetsnbextension --sys-prefix
