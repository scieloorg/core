#!/bin/bash

# Change this value to the local ethernet.
ethernet=wlp0s20f3

# Linux IP.
export IP=$(/sbin/ip -o -4 addr list $ethernet | awk '{print $4}' | cut -d/ -f1)

# Mac OS IP.
#export IP=$(ifconfig $ethernet | grep inet | grep -v inet6 | awk '{print $2}')

export DATABASE_URL=postgres://GVRFlLmcCNfGLhsFvSnCioYOPJPYpyfj:BQ4hSUL4rdj5WZLdR8ilDLRQMvCtzo0caMaXDO0olGsmycQjlcZlTVK9DepZR8kk@$IP:5432/scielo_core
export CELERY_BROKER_URL=redis://$IP:6379/0
export USE_DOCKER=no
export IPYTHONDIR=/app/.ipython
export REDIS_URL=redis://$IP:6379/0
export CELERY_FLOWER_USER=PhFRdLexbrsBvrrbSXxjcMMOcVOavCrZ
export CELERY_FLOWER_PASSWORD=QgScyefPrYhHgO6onW61u0nazc5xdBuP4sM7jMRrBBFuA2RjsFhZLp7xbVYZbrwR
export EMAIL_HOST=$IP
export SOLR_URL=http://$IP:8983/solr/


docker stop scielo_core_local_django
# workon scms
python manage.py runserver_plus 0.0.0.0:8000
