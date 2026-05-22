import datetime
import calendar

def get_epi_week_data(fecha):
    """
    Calcula el número de SE y el año epidemiológico.
    Regla: La SE 1 es la que contiene el primer jueves del año.
    Las semanas comienzan en DOMINGO.
    """
    anio = fecha.year
    
    def inicio_se_1(year):
        # El 4 de enero siempre está en la SE 1 (porque contiene el primer jueves)
        cuatro_enero = datetime.date(year, 1, 4)
        # weekday() de Python: 0=Lun... 6=Dom. 
        # Para que el domingo sea el inicio (retroceso):
        # Si 4 de enero es Lunes (0), retroceso 1 -> Domingo 3
        # Si 4 de enero es Domingo (6), retroceso 0 -> Domingo 4
        retroceso = (cuatro_enero.weekday() + 1) % 7 
        return cuatro_enero - datetime.timedelta(days=retroceso)

    inicio_actual = inicio_se_1(anio)
    
    # Si la fecha es anterior al inicio de la SE 1 del año actual, pertenece al anterior
    if fecha < inicio_actual:
        inicio_anterior = inicio_se_1(anio - 1)
        dias = (fecha - inicio_anterior).days
        return (dias // 7) + 1, anio - 1
    
    # Si la fecha es posterior o igual al inicio de la SE 1 del año siguiente
    inicio_proximo = inicio_se_1(anio + 1)
    if fecha >= inicio_proximo:
        return 1, anio + 1
    
    # Caso normal dentro del año
    dias = (fecha - inicio_actual).days
    return (dias // 7) + 1, anio

def format_df_spanish(df):
    """
    Formatea las columnas numéricas de un DataFrame al estilo español/argentino:
    - Decimales: ,
    - Miles: .
    - Enteros: sin decimales (ej: 72 en lugar de 72.00)
    - Redondeo a 2 dígitos para decimales.
    """
    import pandas as pd
    format_dict = {}
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            # Verificar si la columna es de tipo entero
            if pd.api.types.is_integer_dtype(df[col]):
                format_dict[col] = "{:,.0f}"
            else:
                # Para floats, verificar si todos los valores (no nulos) son enteros
                # o si la columna tiene NaNs pero los valores son enteros
                non_nulls = df[col].dropna()
                if not non_nulls.empty and (non_nulls % 1 == 0).all():
                    format_dict[col] = "{:,.0f}"
                else:
                    format_dict[col] = "{:,.2f}"
    
    return df.style.format(format_dict, decimal=',', thousands='.')
