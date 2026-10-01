### Lista de tareas

- [x] Visualización de archivo .md dentro de ventana emergente
- [x] Agregar mas espacio entre cada mensaje, añadir un recuadro en cada mensaje
- [x] Redimmencionamiento de caja de chat y de archivos con elementos repsonsivos
- [x] Cambiar cursor para identificar que se puede redimensionar la ventana: 
  - Estado (Valor OSC 22)	Dirección del cambio de tamaño	Aspecto Visual Típico
  ew-resize o col-resize	Horizontal (Izquierda / Derecha)	Flecha doble horizontal (↔)
- [x] Ocultar Menu de notas con control + B ademas de añadir una opción visual para la misma tarea en la esquina superior derecha del menu de archivos
- [x] Notificaciones que son iguales no deben mostrarse mas de una vez si la acción se repite mientras aun esta la primera notificación, si hay otra notificacion por una acción diferente si.
- [x] Base de datos SQLite diferente de las notas dentro de DB donde se almacenen configuraciones e historial de chats
  - [x] tabla especificas con chats y normalizada
  - [x] Configuraciones BASICAS como el directorio actual(modifica en el codigo para que tome la opción siempre de la base de datos)
- [x] Menu lateral desplegable con opción de ir a configuración e historial de chats
- [x] Almacenamiento de chat en historial: cuando un usuario abre un nuevo chat no se debe guardar automaticamente en la sesión, lo que debe hacer es enviar un primer mensaje y el chat se guardará con el:
  - [x] id 
  - [x] nombre (generado a partir del primer mensaje)
  - [x] modelo usado
  - [x] Tabla normalizada en sqlite:
    - [x] Id mensaje
    - [x] remitente
    - [x] mensaje (texto plano)
    - [x] hora (mostrar en el chat)
- []Al iniciar un nuevo chat se debe un mensaje de bienvenida dependiendo de la hora del dia, y personalizarlo, no se debe motrar un supuesto mensaje enviado por el usuario: 
    - El mensaje debe estar escrito con letra grande en el centro del chat 
    - Cuando el usuairo escriba un mensaje se de quitar ese mensaje de bienvenida
