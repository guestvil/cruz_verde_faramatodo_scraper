from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright._impl._errors import TimeoutError, Error
import re
import json
from datetime import datetime

cruz_verde_categorias = ['https://www.cruzverde.com.co/medicamentos/', 
                         'https://www.cruzverde.com.co/vital/', 
                         'https://www.cruzverde.com.co/dermocosmeticos/', 
                         'https://www.cruzverde.com.co/cuidado-personal/', 
                         'https://www.cruzverde.com.co/bebe-y-maternidad/', 
                         'https://www.cruzverde.com.co/bienestar-y-nutricion/', 
                         'https://www.cruzverde.com.co/nutricion-deportiva-y-saludable/', 
                         'https://www.cruzverde.com.co/salud-sexual/', 
                         'https://www.cruzverde.com.co/belleza/', 
                         'https://www.cruzverde.com.co/alimentos-y-bebidas/']


def get_x_alone(product_name):
    new_name = 'X'
    flag = False
    some_text = product_name.split()
    for word in range(len(some_text)):
        if some_text[word].lower().startswith('x'):
            try: 
                new_name = new_name + re.sub(r'\D', '', some_text[word+1])
                return new_name
            except IndexError as e:
                return new_name
    return new_name


def get_products_from_page(products_grid_html, python_dictionary, subcat_link, browser):
    ''''Takes the grid html in which the products are displayed, takes the urls for each products, visits them, 
    and retrieves the registro sanitario, name, price and URL. Updates a dicionary which keys are the registro
    sanitario'''
    products_grid_bs = BeautifulSoup(products_grid_html, 'html.parser')
    link_products = []
    duplicates = []
    # The links for all the displayed products are extracted
    for rel_link in products_grid_bs.find_all('a', {'class': 'font-open flex items-center text-main text-16 sm:text-18 leading-20 font-semibold ellipsis hover:text-accent'}):
        #Since the links are relative and begin with /, and the subcat_links end with /, to avoid '//' in the link, the first '/' in rel_link is removed
        product_link = subcat_link + rel_link['href'][1:]
        link_products.append(product_link)
        # print(link_products)
#    pages_products = [browser.new_page() for _ in link_products]
    for a_url in link_products:
        a_page = browser.new_page()
        try: 
            a_page.goto(a_url)
        except TimeoutError as e:
            print('El producto se demoró mucho en cargar:\n')
            print(a_url)
            continue
        if a_page.get_by_role('button', name='Aceptar').is_visible():
            a_page.get_by_role('button', name='Aceptar').click()
        product_html = a_page.locator('section.grid.grid-cols-2.gap-30.pt-60.pb-70.atomic-container.ng-star-inserted').inner_html()
        product_bs = BeautifulSoup(product_html, 'html.parser')
        product_name = product_bs.h1.get_text()
        try: 
            product_invima = product_bs.find('span', {'class': 'text-12 text-gray-dark ng-star-inserted'}).get_text()
        except AttributeError as e:
            print('No se encontró el registro INVIMA para el siguiente producto: \n')
            print({a_url})
            product_invima = None
        if product_invima.split(' ')[0] == 'INVIMA':
            product_invima = product_invima.split(' ')[1]
        product_invima = product_invima.replace(" ", "")
        try:
            product_price = product_bs.find('span', {'class': 'font-bold text-prices'}).get_text().replace('$', '').replace('.', '').replace(' ', '')
        except AttributeError as e:
            print(f'No se encontró el precio en este html para el producto {a_url} \n')
            print(product_bs.find('span', {'class': 'font-bold text-prices'}))
            product_price = None
        product_url = a_url
        if product_invima in python_dictionary.keys():
            # This takes the name already in the dictionary, e.g, MEDICATION X 30 and returns X 30 only
            old_name = get_x_alone(python_dictionary[product_invima][0])
            # The X30 is added to the INVIMA code, and this is the new key for that product
            python_dictionary[product_invima + old_name] = python_dictionary.pop(product_invima)
            #print(product_url)
            #print(product_invima + old_name)
            # The INVIMA code in the current product is changed so that in includes the name, INVIMAX10
            product_invima = product_invima + get_x_alone(product_name=product_name)
            #print(product_invima)
        if product_invima is not None:
            python_dictionary[product_invima]= [product_name, product_price, product_url]
            print('Invima: ', product_invima, '\n', 'Nombre: ', product_name, '\n', 'Precio: ', product_price, '\n')
        a_page.close()
    # print(duplicates)
    return python_dictionary


def get_products_cruz_verde(url, products_dictionary):
    with sync_playwright() as p:
        # This section simply creates a browser to visit a section in CV website
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.get_by_role('button', name='Aceptar').click()
        #This locator allow us to extract the html from a scrolling list
        table_html = page.locator('div.bg-white.z-0.overflow-y-auto.rounded-b-sm.transform.-translate-y-5.px-10.pb-15.pt-25.animate-fade-in-fast').inner_html()
        table_bs = BeautifulSoup(table_html, 'html.parser')
        # We iterate over all the links in the list, these are links to sub-categories
        for links in table_bs.find_all('a'):
            # print(links)
            #The links are relative links, so they must be added to the base link
            subcat_link = 'https://www.cruzverde.com.co' + links['href']
            # Each link is then opened in a browser
            p = browser.new_page()
            p.goto(subcat_link)
            if p.get_by_role('button', name='Aceptar').is_visible():
                p.get_by_role('button', name='Aceptar').click()
            # This locator points to the html grid in which individual products are desplayed and extracts it
            is_final_page = False
            counter = 0
            while is_final_page == False:
                counter += 1
                if counter > 100:
                    break
                try: 
                    products_grid_html = p.locator('div.grid.grid-cols-4.gap-50.ng-star-inserted > div.col-span-4.lg\:col-span-3').inner_html()
                except TimeoutError as e:
                    print(f'Error en {subcat_link} en la página {counter}')
                    print('Tiempo excedido en este locator: div.grid.grid-cols-4.gap-50.ng-star-inserted > div.col-span-4.lg\:col-span-3')
                    continue
                get_products_from_page(products_grid_html=products_grid_html, python_dictionary=products_dictionary, subcat_link=subcat_link, browser=browser)
                #print('12 productos añadidos')
                button_exist = p.locator('g#at-ico-double-angle-right').count()
                if button_exist != 0:
                    is_final_page = False
                if button_exist == 0:
                    is_final_page = True
                    break
                try: 
                    p.locator('div.rounded-full.bg-quaternary.ml-15.lg\:h-32.lg\:w-32.h-25.w-25.flex.items-center.justify-center.cursor-pointer.hover\:bg-prices.text-white.ng-star-inserted').nth(-2).click()
                except TimeoutError as e: 
                    #print('El botón de avanzar no está habilitado')
                    break
            p.close()
        browser.close()
    return products_dictionary


def main():
    cruz_verde_productos = {}
    for link in cruz_verde_categorias:
        get_products_cruz_verde(link, cruz_verde_productos)
    with open('cruz_verde_completo.json', 'w') as file:
        json.dump(cruz_verde_productos, file)
        print('PROGRAMA EXITOSO, archivo guardado en cruz_verde_completo.json')
        print('Hora de inicio {inicio}, hora final: {final}')

if __name__ == '__main__':
    main()

