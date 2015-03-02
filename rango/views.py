from django.template import RequestContext
from django.shortcuts import render_to_response, redirect
from django.http import HttpResponse, HttpResponseRedirect
from rango.models import Category, Page, UserProfile  
from rango.forms import CategoryForm, PageForm, UserForm, UserProfileForm
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from datetime import datetime
from rango.bing_search import run_query
from django.contrib.auth.models import User



def index(request):
    # Obtain the context from HTTP request.
    context = RequestContext(request)
    context_dict = {}
    # request.session.set_test_cookie()

    # Query the database for a list of ALL categories currently stored.
    # Order the categories by no. likes in descending order.
    # Retrieve the top 5 only - or all if less than 5.
    # Place the list in our context_dict dictionary which will be passed to the template engine.
    cat_list = get_category_list() #Category.objects.order_by('-likes')[:5]
    top_five = cat_list[:5]
    page_list = Page.objects.order_by('-views')[:5]
    # context_dict = {'categories': category_list, 'pages': page_list}
    context_dict['cat_list'] = cat_list
    context_dict['top_five'] = top_five
    context_dict['pages'] = page_list

    # We loop through each category returned, and create a URL attribute.
    # This attribute stores an encoded URL (e.g. spaces replaced with underscores).
    # for category in category_list:
    #     category.url = en_de(category.name, True)

    if request.session.get('last_visit'):
        last_visit_time = request.session.get('last_visit')
        visits = request.session.get('visits', 0)

        if (datetime.now() - datetime.strptime(last_visit_time[:-7], "%Y-%m-%d %H:%M:%S")).days >0:
            request.session['visits'] = visits + 1
            request.session['last_visit'] = str(datetime.now())
    else:
        request.session['last_visit'] = str(datetime.now())
        request.session['visits'] = 1

    return render_to_response('rango/index.html', context_dict, context)

    """The following lines implement (client-side)cookie-based session:"""
    # # Render the response and return to the client.
    # response = render_to_response('rango/index.html', context_dict, context)
    
    # # Get the number of visits to the site.
    # # We use the COOKIES.get() function to obtain the visits cookie.
    # # If the cookie exists, the value returned is casted to an integer.
    # # If the cookie doesn't exist, we default to zero and cast that.
    # visits = int(request.COOKIES.get('visits', '0'))
    # # Does the cookie last_visit exist?
    # if 'last_visit' in request.COOKIES:
    #     last_visit = request.COOKIES['last_visit']
    #     last_visit_time = datetime.strptime(last_visit[:-7], "%Y-%m-%d %H:%M:%S")

    #     # If it's been more than a day since the last visit...
    #     if (datetime.now() - last_visit_time).days > 0:
    #         # ...reassign the value of the cookie to +1 of what it was before...
    #         response.set_cookie('visits', visits+1)
    #         # ...and update the last visit cookie, too.
    #         response.set_cookie('last_visit', datetime.now())
    # else:
    #     # Cookie last_visit doesn't exist, so create it to the current date/time.
    #     response.set_cookie('last_visit', datetime.now())

    # return response

def get_category_list():
    # context = RequestContext(request)
    category_list = Category.objects.all()

    for cat in category_list:
        cat.url = en_de(cat.name, True)
    return category_list

def about(request):
    context = RequestContext(request)

    cat_list = get_category_list()
    
    if request.session.get('visits'):
        count = request.session.get('visits')
    else:
        count = 0

    context_dict = {'boldmessage': 'Ths is to test the about page', 'visits': count, 'cat_list': cat_list}
    return render_to_response('rango/about.html', context_dict, context)
    # return HttpResponse("""Rango says: Here is the about page.
    #                   <p> <a href="/rango/">Index</a> </p>""")

def category(request, category_name_url):
    # Request our context from the request passed to us.
    context = RequestContext(request)

    # Change underscores in the category name to spaces.
    # URLs don't handle spaces well, so we encode them as underscores.
    # We can then simply replace the underscores with spaces again to get the name.
    category_name = en_de(category_name_url, False)
    cat_list = get_category_list()

    # Create a context dictionary which we can pass to the template rendering engine.
    # We start by containing the name of the category passed by the user.
    context_dict = {'category_name': category_name, 'category_name_url': category_name_url, 'cat_list': cat_list}
    
    try:
        # Can we find a category with the given name?
        # If we can't, the .get() method raises a DoesNotExist exception.
        # So the .get() method returns one model instance or raises an exception.
        category = Category.objects.get(name__iexact=category_name)

        # Retrieve all of the associated pages.
        # Note that filter returns >= 1 model instance.
        pages = Page.objects.filter(category=category).order_by('-views')

        # Adds our results list to the template context under name pages.
        context_dict['pages'] = pages

        # We also add the category object from the database to the context dictionary.
        # We'll use this in the template to verify that the category exists.
        context_dict['category'] = category
        # context_dict['category_name_url'] = category_name_url
    except Category.DoesNotExist:
        # We get here if we didn't find the specified category.
        # Don't do anything - the template displays the "no category" message for us.
        pass

    if request.method == 'POST':
        query = request.POST['query'].strip()

        if query:
            result_list = run_query(query)
            context_dict['result_list'] = result_list

    # Go render the response and return it to the client.
    return render_to_response('rango/category.html', context_dict, context)

def en_de(name, value):
    if value:
        new = name.replace(' ', '_')
    else:
        new = name.replace('_', ' ')
    return new

def add_category(request):
    context = RequestContext(request)
    cat_list = get_category_list()
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save(commit=True)
            return index(request)
        else:
            print form.errors
    else:
        form = CategoryForm()

    return render_to_response('rango/add_category.html', {'form': form, 'cat_list': cat_list}, context)

def add_page(request, category_name_url):
    context = RequestContext(request)
    category_name = en_de(category_name_url, True)
    cat_list = get_category_list()
    if request.method == 'POST':
        form = PageForm(request.POST)

        if form.is_valid():
            page = form.save(commit=False)

            try:
                cat = Category.objects.get(name=category_name)
                page.category = cat
            except Category.DoesNotExist:
                return render_to_response('rango/add_category.html', {'cat_list': cat_list}, context)

            page.views = 0
            page.save()

            return HttpResponse("Page Added!")   #category(request, category_name_url)
        else:
            print form.errors
    else:
        form = PageForm()

    return render_to_response('rango/add_page.html', 
        {'category_name_url': category_name_url, 'category_name': category_name, 'form': form, 'cat_list': cat_list}, context)

def register(request):
    context = RequestContext(request)
    # if request.session.test_cookie_worked():
    #     print ">>>> TEST COOKIE WORKED!"
    #     request.session.delete_test_cookie
    cat_list = get_category_list()

    registered = False
    if request.method == 'POST':
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            user.set_password(user.password)
            user.save()

            profile = profile_form.save(commit=False)
            profile.user = user

            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']

            profile.save()
            registered = True
        else:
            print user_form.errors, profile_form.errors
    else:
        user_form = UserForm()
        profile_form = UserProfileForm()

    return render_to_response('rango/register.html', 
        {'user_form': user_form, 'profile_form': profile_form, 'registered': registered, 'cat_list': cat_list}, context)

def user_login(request):
    context = RequestContext(request)
    cat_list = get_category_list()
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(username=username, password=password)
        
        if user:
            if user.is_active:
                login(request, user)
                return HttpResponseRedirect('/rango/')
            else:
                return HttpResponse('Your Rango account is disabled.')
        else:
            print "Invalid login details: {0}, {1}".format(username, password)
            return HttpResponse("Invalid username or password.")
    else:
        return render_to_response('rango/login.html', {'cat_list': cat_list}, context)

@login_required
def restricted(request):
    context = RequestContext(request)
    cat_list = get_category_list()
    return render_to_response('rango/restricted.html', {'cat_list': cat_list}, context)


@login_required
def user_logout(request):
    logout(request)
    return HttpResponseRedirect('/rango/')

def search(request):
    context = RequestContext(request)
    cat_list = get_category_list()
    result_list = []

    if request.method == 'POST':
        query = request.POST['query'].strip()

        if query:
            result_list = run_query(query)

    return render_to_response('rango/search.html', {'result_list': result_list,'cat_list': cat_list}, context)

def profile(request):
    context = RequestContext(request)
    cat_list = get_category_list()
    context_dict = {'cat_list': cat_list}
    u = User.objects.get(username=request.user)

    try:
        up = UserProfile.objects.get(user=u)
    except:
        up = None

    context_dict['user'] = u
    context_dict['userprofile'] = up
    return render_to_response('rango/profile.html', context_dict, context)

def track_url(request):
    context = RequestContext(request)
    page_id = None
    url = '/rango/'
    if request.method == 'GET':
        if 'page_id' in request.GET:
            page_id = request.GET['page_id']
            try:
                page = Page.objects.get(id=page_id)
                page.views = page.views + 1
                page.save()
                url = page.url
            except:
                pass

    return redirect(url)

def track_category_url(request):
    context = RequestContext(request)
    cat_id = None
    url = '/rango/category/'
    if request.method == 'GET':
        if 'cat_id' in request.GET:
            cat_id = request.GET['cat_id']
            try:
                category = Category.objects.get(id=cat_id)
                category.views = category.views + 1
                category.save()
                url = category.url
            except:
                pass
    return redirect(url)

@login_required
def like_category(request):
    context = RequestContext(request)
    cat_id = None
    if request.method == 'GET':
        cat_id = request.GET['category_id']
    likes = 0

    if cat_id:
        category = Category.objects.get(id=int(cat_id))
        if category:
            likes = category.likes + 1
            category.likes = likes
            category.save()

    return HttpResponse(likes)
