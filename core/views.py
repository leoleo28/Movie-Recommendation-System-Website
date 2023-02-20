from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.contrib import messages
from .models import Movie
import pickle
import requests
from transformers import AutoTokenizer
from transformers import AutoModelForSequenceClassification
from scipy.special import softmax
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity


movies=pickle.load(open('model/movies.pkl','rb'))
cv = CountVectorizer(max_features=5000,stop_words='english')
matrix = cv.fit_transform(movies["new_features"])
similarity = cosine_similarity(matrix)
sorted_name=pickle.load(open('model/sorted_name.pkl','rb'))
sorted_name=list(sorted_name)
review_1=pickle.load(open('model/review_1.pkl','rb'))
review_2=pickle.load(open('model/review_2.pkl','rb'))
imdb_id=pickle.load(open('model/IMDB_id.pkl','rb'))

class MOVIE():
    def __init__(self, name, image):
        self.name=name
        self.image=image

class COMMENT():
    def __init__(self,text,sentiment):
        self.text=text
        self.sentiment=sentiment

class ACTOR():
    def __init__(self,name,image):
        self.name=name
        self.image=image

def get_url(movie_id):
    url = "https://api.themoviedb.org/3/movie/{}?api_key=a65e4b33e800212c365ef0c02aa2d6d8&language=en-US".format(movie_id)
    data = requests.get(url).json()
    if 'poster_path' not in data:
        return ""
    poster_path = str(data['poster_path'])
    if poster_path.endswith(".jpg"):
        return "https://image.tmdb.org/t/p/w500/" + poster_path
    else:
        return ""

def index(request):
    if request.method =='POST':
        selected_movie=request.POST['selected_movie']
        Select_mv=Movie.objects.filter(name=selected_movie).first()
        if selected_movie=="" or Select_mv==None:
            messages.info(request, 'Plsease enter or select a movie from the dropdown')
            return redirect('/')
        else:
            id=movies.iloc[movies[movies['title'] == selected_movie].index[0]].id
            index= movies[movies['title'] == selected_movie].index[0]  
            url=get_url(id)
            text=str(movies.iloc[index].overview)
            director, date, runtime, rate, genres = show_info(index)

            get_trailer_url=get_trailer(id)
            if get_trailer_url=='':
                get_trailer_url='#'

            homepage_link=homepage(selected_movie)
            if homepage_link=='':
                homepage_link='#'

            cast=show_cast_img(selected_movie)
            movie_list = recommend(selected_movie)

            context={
                'url':url,
                'text':text,
                'director':director,
                'date':date,
                'runtime':runtime,
                'rate':rate,
                'genres':genres,
                'get_trailer_url':get_trailer_url,
                'homepage_link':homepage_link,
                'cast':cast,
                'selected_movie':selected_movie,
                'movie_list':movie_list,
            }
            return redirect('/frontpage/'+selected_movie)
    else:
        all_movies=Movie.objects.all()
        return render(request,'list.html',{'all':all_movies})

def mcomment(request,pk):
    movie=pk
    id=movies.iloc[movies[movies['title'] == movie].index[0]].id
    img_url=get_url(id)
    L=[]
    if movie in review_1:
        for h in review_1[movie]:
            if type(h)==float:
                break
            else:
                L.append(h)
    else:
        for h in review_2[movie]:
            if type(h)==float:
                break
            else:
                L.append(h)
    
    MODEL = f"cardiffnlp/twitter-roberta-base-sentiment"
    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL)
    result_ls=[]
    for reviews in L:
        encoded_text = tokenizer(reviews, return_tensors='pt')
        output = model(**encoded_text)
        scores = output[0][0].detach().numpy()
        scores = softmax(scores)
        scores_dict = {
            'Sentiment: Negative ☹️' : scores[0],
            'Sentiment: Neutral 😑' : scores[1],
            'Sentiment: Positive 🙂' : scores[2]
        }
        result = max(scores_dict, key=scores_dict.get)
        add_item=COMMENT(reviews,result)
        result_ls.append(add_item)
    return render(request,'comment.html',{'all':result_ls,'movie':movie,'img_url':img_url})


def recommend(movie):
    index = movies[movies['title'] == movie].index[0]
    distances = sorted(list(enumerate(similarity[index])), reverse=True, key=lambda x: x[1])
    L=[]
    contain=[]
    contain.append(movie)
    for i in distances:
        movie_id = movies.iloc[i[0]].id
        movie_name=movies.iloc[i[0]].title
        url=get_url(movie_id)
        if movie_name in contain or url=="":
            continue
        else:
            add_item=MOVIE(movie_name,url)
            L.append(add_item)
            contain.append(movie_name)
            if len(L)==7:
                break
    return L

def show_info(index):
    data=movies.iloc[index]
    director, date, runtime, rate, genres = ['']*5
    if len(data.director)>0:
        director=data.director[0]
    director='Director: '+director
    date=str(data.release_date)
    date=date[:4]
    runtime=str(int(data.runtime))
    runtime+= ' minutes'
    rate=str(data.vote_average)

    for genre_type in data.genres:
        genres=genres+ genre_type+', '
    genres=genres[:-2]
    genres='Genres: '+genres 
    return director, date, runtime, rate, genres

def get_trailer(movie_id):
    url="https://api.themoviedb.org/3/movie/{}/videos?api_key=a65e4b33e800212c365ef0c02aa2d6d8&language=en-US".format(movie_id)
    data = requests.get(url).json()
    if 'results' not in data:
        return ''
    if len(data['results'])>0 and 'key' in data['results'][0]:
        suffix = data['results'][0]['key']
        url="https://www.youtube.com/watch?v="+suffix
        return url
    else:
        return ''

def homepage(movie):
    homepage_link=imdb_id[movie].to_string()[5:]
    if homepage_link.startswith('tt'):
        return "https://www.imdb.com/title/"+homepage_link+ "/?ref_=tt_urv"
    else:
        return ''

def show_cast_img(movie):
    index = movies[movies['title'] == movie].index[0]  
    movie_id=movies.iloc[index].id
    url='https://api.themoviedb.org/3/movie/{}/credits?api_key=a65e4b33e800212c365ef0c02aa2d6d8&language=en-US'.format(movie_id)
    data = requests.get(url).json()
    L=[]
    if 'cast' not in data:
        return L
    for cast in data['cast']:
        if type(cast['profile_path'])!=str:
            continue
        url_img="https://image.tmdb.org/t/p/w500"+cast['profile_path']
        add_item=ACTOR(cast['name'],url_img)
        L.append(add_item)
        if len(L)==5:
            break
    return L

def frontpage(request,pk):
    selected_movie=pk
    id=movies.iloc[movies[movies['title'] == selected_movie].index[0]].id
    index= movies[movies['title'] == selected_movie].index[0]  
    url=get_url(id)
    text=str(movies.iloc[index].overview)
    director, date, runtime, rate, genres = show_info(index)

    get_trailer_url=get_trailer(id)
    if get_trailer_url=='':
        get_trailer_url='#'

    homepage_link=homepage(selected_movie)
    if homepage_link=='':
        homepage_link='#'

    cast=show_cast_img(selected_movie)
    movie_list = recommend(selected_movie)

    context={
        'url':url,
        'text':text,
        'director':director,
        'date':date,
        'runtime':runtime,
        'rate':rate,
        'genres':genres,
        'get_trailer_url':get_trailer_url,
        'homepage_link':homepage_link,
        'cast':cast,
        'selected_movie':selected_movie,
        'movie_list':movie_list,
    }
    return render(request,'frontpage.html', context)

