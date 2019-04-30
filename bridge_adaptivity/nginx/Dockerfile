ARG bridge_adaptivity_image=bridge_adaptivity
FROM $bridge_adaptivity_image as bridge

FROM nginx

RUN apt-get update && apt-get install -y vim
RUN rm /etc/nginx/conf.d/default.conf

ARG build_env=prod
ADD $build_env/* /etc/nginx/conf.d/

RUN mkdir /etc/nginx/ssl

COPY --from=bridge /www/static /www/static
