from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright._impl._errors import TimeoutError, Error
import json
import re
from datetime import datetime

farmatodo_link = 'https://www.farmatodo.com.co'

farmatodo_categorias = ['https://www.farmatodo.com.co/categorias/salud-y-medicamentos',
                        'https://www.farmatodo.com.co/categorias/bienestar-y-nutricion-deportiva',
                        'https://www.farmatodo.com.co/categorias/belleza/ojos',
                        'https://www.farmatodo.com.co/categorias/cuidado-del-bebe',
                        'https://www.farmatodo.com.co/categorias/cuidado-personal',
                        'https://www.farmatodo.com.co/categorias/dermocosmetica']


def get_x_alone(product_name):
    '''Takes a name such as drug X 30 and returns only X30
    This is to tell apart two products with the same INVIMA code but differente quantity.'''
    new_name = 'X'
    some_text = product_name.split()
    for word in range(len(some_text)):
        if some_text[word].lower().startswith('x'):
            try: 
                new_name = new_name + re.sub(r'\D', '', some_text[word+1])
                return new_name
            except IndexError as e:
                return new_name
    return new_name


def load_page_with_retry(page, url, retries=3):
    """
    Tries to load a page with retries if timeout occurs.
    
    :param page: Playwright page object
    :param url: URL to navigate to
    :param retries: Number of retry attempts
    :param timeout: Timeout for each attempt in milliseconds
    """
    for attempt in range(retries):
        try:
            # page.route("**/*", lambda route, request: route.abort() if request.resource_type == "image" else route.continue_())
            page.goto(url)
            return  # Exit the function if successful
        except TimeoutError:
            print(f"TimeoutError on attempt {attempt + 1}. Retrying...")
            if attempt == retries - 1:  # On the last attempt, re-raise the exception
                raise
    return None


def get_products_from_page(grid_html, python_dictionary, base_link, playwright_browser):
    '''grid_html = an html of the grid in which all products are displayed in the site
    base_link: farmatodo url
    It itirates over all the product links in the grid and stores their information.'''
    counter = 0
    counter_products = 0
    farmadoto_products_links = []
    counter_no_invima = 0
    grid_bs = BeautifulSoup(grid_html, 'html.parser')
    for a_link in grid_bs.find_all('a', {'class': 'content-product'}):
        product_link = base_link + a_link['href']
        farmadoto_products_links.append(product_link)
    for product_link in farmadoto_products_links:
        counter += 1
        print(f'Se hicieron {counter} ciclos')
        product_page = playwright_browser.new_page()
        product_page.route("**/*", lambda route, request: route.abort() if request.resource_type == "image" else route.continue_())
        try: 
            product_page.goto(product_link)
        except TimeoutError as e:
            print('Se demoró mucho en cargar: \n', product_link)
            continue
        except Error as e:
            print(e)
            print('Error con el producto: ', product_link)
        try:
            product_html = product_page.locator('div.col-12.col-lg-4.px-0.py-2.py-lg-5').inner_html()
        except TimeoutError as e:
            print(f'El producto {product_link} tomó demasiado tiempo en cargar')
            continue
        except Error as e:
            print('Something happened: ', e)
            continue
        product_bs = BeautifulSoup(product_html, 'html.parser')
        try:
            product_invima = product_bs.find('div', class_='title', string=re.compile(r'^Registro Invima:\s*$')).find_next('div', class_='description').get_text()
            counter_no_invima = 0
        except AttributeError as e:
            print(f'No se encontró el registro Invima para el producto: \n')
            print(product_link, '\n')
            product_invima = "None"
            counter_no_invima += 1
            if counter_no_invima > 15:
                return python_dictionary
        try:
            product_name = product_bs.h1.get_text()
        except AttributeError as e:
            print('No se encontró el nombre del siguiente producto:\n')
            print(product_link, '\n')
            product_name = 'None'
        product_price_html = product_page.locator('div.fixed-panel').inner_html()
        product_price_bs = BeautifulSoup(product_price_html, 'html.parser')
        try:
            product_price = product_price_bs.find('span', {'class': 'box__price--current'}).get_text().replace('.', '').replace('$', '')
        except AttributeError as e:
            print('No se encontró el precio del siguiente producto: \n')
            print(product_link, '\n')
            product_price = 'None'
        if product_invima in python_dictionary.keys():
            # This takes the name already in the dictionary, e.g, MEDICATION X 30 and returns X 30 only
            old_name = get_x_alone(python_dictionary[product_invima][0])
            # The X30 is added to the INVIMA code, and this is the new key for that product
            python_dictionary[product_invima + old_name] = python_dictionary.pop(product_invima)
            # The INVIMA code in the current product is changed so that in includes the name, INVIMAX10
            product_invima = product_invima + get_x_alone(product_name=product_name)
        if product_invima != 'None' and product_price != 'None':
            python_dictionary[product_invima]= [product_name, product_price, product_link]
            counter_products += 1
            print('Invima: ', product_invima, '\n', 'Nombre: ', product_name, '\n', 'Precio: ', product_price, '\n')
        product_page.close()
    return python_dictionary


def get_html_from_locator_retry(locator_string, playwright_page, current_url):
    ''' Sometimes the page layout changes, this functions makes sure that those cases are handled.
    locator_string: string with a locator in playwright
    playwright_page: a playwright page'''
    counter = 0
    while counter < 5:
        try: 
            html = playwright_page.locator(locator_string).inner_html()
            return html
        except TimeoutError as e:
            counter += 1
            print('Intento {counter}, No se encontró el html de la lista en {current_url}')
            html = 'None'
            playwright_page.goto(current_url, wait_until='load')
    return html


def get_products_farmatodo(url, products_dicionary):
    with sync_playwright() as p:
        browswer = p.chromium.launch(headless=True)
        page = browswer.new_page()
        load_page_with_retry(page=page, url=url)
        list_html = get_html_from_locator_retry(locator_string='div.container-fluid.cont-filtres-categories', playwright_page=page, current_url=url)
        if list_html == 'None':
            print('No se encontró la lista para {url}, estos productos NO SE INCLUYEN')
            return products_dicionary
        #try:
         #   list_html = page.locator('div.container-fluid.cont-filtres-categories').inner_html()
        #except TimeoutError as e: 
         #   print(f'Ni si quiera se encontró el html de la lista de productos de esta {url}')
        list_bs = BeautifulSoup(list_html, 'html.parser')
        for button in list_bs.find_all('h5'):
            print(button.get_text())
            try:
                page.locator('h5.title-filtres', has_text=button.get_text().strip()).click()
            except Error as e:
                print(e)
                print('No se le pudo dar click a: ', button.get_text())
                continue
            # page.get_by_role('button', name='Cargar más').click()
            counter = 0
            attemps = 0
            while attemps < 3:
                counter += 1
                #if counter % 10 == 0:
                   # print('10 ciclos de scroll')
                # Scroll to the bottom of the page
                try: 
                    page.evaluate("window.scrollBy(0, document.body.scrollHeight);")
                except Error as e:
                    print('Stoped scroll, something happened: {e}')
                    break
                # Wait for new content to load
                page.wait_for_timeout(5000)  # Adjust timeout as needed
                try:    
                    if page.get_by_text(' No se han encontrado más resultados').is_visible() or page.get_by_text('No se han encontrado más resultados').is_visible():
                       #print("Reached the end of the page.")
                        break
                except TimeoutError as e:
                    print(e)
                    continue
                if page.get_by_role('button', name='Cargar más ').is_visible():
                    try: 
                        page.get_by_role('button', name='Cargar más ').click()
                        #print('Cargar más')
                    except TimeoutError as e:
                        print('El botón de cargar más no está habilitado en: \n')
                        #print(button.get_text())
                if counter % 300 == 0:
                    attemps += 1
                    page.locator('h5.title-filtres', has_text=button.get_text().strip()).click()
            try: 
                page_grid_html = page.locator('div.row.cont-group-view').inner_html()
            except TimeoutError as e:
                print('Error encontrando este locator: div.row.cont-group-view en la categoría', button.get_text())
                print('La URL del error es:', url)
                continue
            except Error as e:
                page_grid_html=None
                print('Error encontrando el locator del grid en la categoría', button.get_text())
            if page_grid_html is not None:
                get_products_from_page(page_grid_html, products_dicionary, farmatodo_link, browswer)
        dict_size = len(products_dicionary.keys())
        print(f'Se almacenaron {dict_size} productos de Farmatodo')
        # let's extract all product information from a subcategory in the site
        browswer.close()
    return products_dicionary


def main():
    farmadoto_productos = {}
    for link in farmatodo_categorias:
        get_products_farmatodo(link, farmadoto_productos)
    with open('farmatodo_completo.json', 'w') as file:
        json.dump(farmadoto_productos, file)
    print('PROGRAMA EXITOSO, archivo guardado en farmatodo_completo.json')


if __name__ == "__main__":
    main()