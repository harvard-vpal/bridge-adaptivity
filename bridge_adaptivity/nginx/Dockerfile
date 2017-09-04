FROM nginx
RUN rm /etc/nginx/conf.d/default.conf
ADD sites-enabled/ /etc/nginx/conf.d

RUN apt-get update && apt-get install -y vim
