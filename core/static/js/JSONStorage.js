'use strict';


class JSONStorage{

    constructor(name, value, storage=window.sessionStorage){
        /*
            Constructor of class JSONStorage.
            Params:
                name: Name of JSON stored
                value: Value in JSON (must be a JavaScript Object)
        */
        let objectConstructor = {}.constructor;

        this.name = name;
        this.value = value;
        this.storage = storage;
        this.flat_obj = {};


        if (value === objectConstructor) {
            console.log("Param value must be a object.");
            return undefined;
        }

        this.storage.setItem(this.name, JSON.stringify(this.value));

    }

    iterate(obj){
        /*
            Iterate by item of an object keeping the attributes shallower.
            Params:
                obj: JavaScript Object
        */
        for (var property in obj) {
            if (obj.hasOwnProperty(property)) {
                if (typeof obj[property] == "object") {
                    this.iterate(obj[property]);
                }
                else {
                    this.flat_obj[property] = obj[property];
                }
            }
        }
        return this.flat_obj;
    }

    setItem(key, val){
        /*
            Function to set a new item in browser local/session storage JSON
            If the name doesnt exists in a local/session storage it will be create
            Params:
                name: Name of the key name in a local/session storage
                key: The key of a new item in a storage
                val: The value of item in a storage
        */
       let jsonObject = {};

       if(!this.storage.getItem(this.name)){
            jsonObject[key] = val;
            this.storage.setItem(this.name, JSON.stringify(jsonObject));
       }else{
            jsonObject = JSON.parse(this.storage.getItem(this.name));
            jsonObject[key] = val;
            this.storage.setItem(this.name, JSON.stringify(jsonObject));
       }

    }

    getItem(key){
        /*
            Function to set a new item in browser storage JSON
            If the name doesnt exists in a storage it will be create
            Params:
                name: Name of the key name in a storage
                key: The key of a new item in a storage
                val: The value of item in a storage
        */
        let jsonObject;

        jsonObject = JSON.parse(this.storage.getItem(this.name));

        return jsonObject[key];

    }

    removeItem(key){
        /*
            Remove an item from the local/session storage.
            Params:
                key: The key of a new item in a local/session storage
        */
        let jsonObject;

        jsonObject = this.get(this.name);

        delete jsonObject[key];

        this.storage.setItem(this.name, JSON.stringify(jsonObject));

    }

    clear(){
        /*
            Remove an item from the storage.
            Params:
                name: Name of the key name in a storage
        */

        return this.storage.removeItem(this.name);

    }

    get(){
        /*
            Function to return the browser local/session storage JSON by name.
            If name of doesnt exists in return ``undefined``
        */

        if(!this.storage.getItem(this.name)){
            return undefined;
        }else{
            return JSON.parse(this.storage.getItem(this.name));
        }

    }

}