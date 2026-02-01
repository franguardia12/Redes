# Requisitos

Para ejecutar este proyecto es necesario contar con:

* Python 3.x instalado
* Librería estándar de sockets de Python

Si además se quiere simular una red con una determinada topología:

* Mininet: herramienta para simular condiciones de red
* xterm: es la terminal gráfica utilizada por Mininet
* Wireshark: herramienta para capturar y analizar tráfico en la red simulada

Estos pueden instalarse ejecutando los siguientes comandos:

sudo apt install python3

sudo apt install mininet

sudo apt install xterm

sudo apt install wireshark

# Ejecución

## Cómo ejecutar el servidor

Para ejecutar el servidor y que este comience a estar activo ejecutar el siguiente comando:

python3 src/start-server.py -H <IP_SERVIDOR> -p <PUERTO> -s <DIRECTORIO_DE_ALMACENAMIENTO>

Donde la IP del servidor es la que se utiliza en Mininet (10.0.0.1 comunmente), el puerto también viene asignado por Mininet (7000 en este caso) y el directorio de almacenamiento es el lugar en el que se guardarán los archivos que estén subidos al servidor (tiene que ser un directorio local). Opcionalmente se puede indicar una flag -v (modo verbose) o -q (modo quiet) lo que indica la cantidad de mensajes a mostrar en la terminal donde se esté ejecutando el servidor

## Cómo ejecutar el cliente

La ejecución del cliente depende de la operación que se quiera realizar con él. En el caso de querer hacer un UPLOAD la ejecución es:

python3 src/upload.py -H <IP_SERVIDOR> -p <PUERTO> -s <DIRECTORIO_DE_ALMACENAMIENTO> -n <NOMBRE_ARCHIVO> -r <PROTOCOLO>

Donde la IP del servidor tiene que ser la misma que se especificó antes para ejecutarlo (al igual que el puerto), el directorio de almacenamiento es el lugar en el que se guardarán los archivos que el cliente haya descargado (o que este tenga previamente y que luego quiera subir al servidor, y que también tiene que ser un directorio local), el nombre del archivo es aquel que se quiera subir al servidor o descargar (y tiene que estar incluido en el directorio anteriormente especificado en el caso de que sea un UPLOAD), y el protocolo es el que se quiera usar en la transmisión del archivo (opciones posibles son SW y GBN). Opcionalmente se puede indicar una flag -v (modo verbose) o -q (modo quiet) lo que indica la cantidad de mensajes a mostrar en la terminal donde se esté ejecutando el cliente

Tanto en el cliente como el servidor se puede especificar un flag -h que da una ayuda de los comandos posibles que se pueden utilizar y lo que hace cada uno
