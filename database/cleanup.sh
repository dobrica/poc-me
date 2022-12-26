arr=`docker inspect  -f '{{ range .Mounts }}{{ .Name }} {{ end }}' mbdb`
sudo docker stop mbdb
sudo docker rm mbdb
for i in ${arr[@]}; do
    sudo docker volume rm $i
done