import json
import csv


def list_of_dictionaries(list_of_files_names):
    a_list = []
    for names in list_of_files_names:
        var_name = names.split('.')[0]
        with open(names, 'r') as file:
            globals()[var_name] = json.load(file)
        a_list.append(globals()[var_name])
    #print('This is the output of the first function:\n')
    #print(a_list)
    return a_list


def compare_invima_and_prices(list_of_dicionaries):
    final_list = [['invima', 'url_cv', 'precio_cv', 'precio_fm', 'url_fm']]
    for invima in list_of_dicionaries[0].keys():
        if invima in list_of_dicionaries[1].keys():
            cv_precio = list_of_dicionaries[0][invima][1]
            fm_precio = list_of_dicionaries[1][invima][1]
            if cv_precio is not None and fm_precio is not None:
                if int(cv_precio) > int(fm_precio):
                    cv_url = list_of_dicionaries[0][invima][2]
                    fm_precio = list_of_dicionaries[1][invima][1]
                    fm_url = list_of_dicionaries[1][invima][2]
                    final_list.append([invima, cv_url, cv_precio, fm_precio,fm_url ])
    #print('This is the output of the second function: \n')
    #print(final_list)
    return final_list


def main():
    files_names = ['cruz_verde_completo.json', 'farmatodo_completo.json']
    list_of_dicts = list_of_dictionaries(files_names)
    list_of_alerts = compare_invima_and_prices(list_of_dicts)
    #print(len(list_of_alerts))
    for lists in list_of_alerts:
        print(lists)
    with open('cruz_verde_farmatodo_precios_completo.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(list_of_alerts)


if __name__ == "__main__":
    main()