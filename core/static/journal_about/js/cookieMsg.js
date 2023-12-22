/*

Warning:
This script should preferably be included at the bottom of the page, before the </body> tag.

*/

"use strict";

var alertMessage = {
  
  isActive: true,
  msgContainer: document.querySelector("div.alert.alert-warning.alert-dismissible"),
  
  setCookie: function (cname, cvalue, exdays){
    var d = new Date();

    d.setTime(d.getTime() + (exdays*24*60*60*1000));
    var expires = "expires="+ d.toUTCString();
    
    document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
  },
  getCookie: function (cname) {
    var name = cname + "=";
    var decodedCookie = decodeURIComponent(document.cookie);
    var ca = decodedCookie.split(';');
    
    for(var i = 0; i <ca.length; i++) {
      
      var c = ca[i];
      
      while (c.charAt(0) == ' ') {
        c = c.substring(1);
      }

      if (c.indexOf(name) == 0) {
        return c.substring(name.length, c.length);
      }
    }
    return "";
  },
  checkCookie: function (cname){
    var cookieName = alertMessage.getCookie(cname);
    
    // If there is no cookie accepting cookie policies, set it.
    if (!(cookieName != "" && cookieName != null)) {

      // show the element
      alertMessage.showAlertMessage();
      
    }else{

      // hide alert-message
      if (typeof msgContainer === 'object' && msgContainer !== null) {
        alertMessage.msgContainer.style.display = 'none';
      }

    }
  },
  clearCookie: function (cname){
    alertMessage.setCookie(cname, "no", -365);
  },
  
  showAlertMessage: function (){

      //checks if there is the alert-message element
      if (typeof msgContainer === 'object' && msgContainer !== null) {
        var el = alertMessage.msgContainer,
            btnClose = el.querySelector('button.close');
      }else{
        var el = null,
            btnClose = null;
      }

      if (el !== null && btnClose !== null) {

        btnClose.addEventListener("click", function() {
          alertMessage.setCookie("alert-message-accepted", "yes", 365);
        });

        el.style.display = "block";

      }else{
        
        //console.error('The alert-message element does not exist'); 

      }
      
  },
  Init: function (){

    if(alertMessage.isActive){
      alertMessage.checkCookie("alert-message-accepted"); 
    }else{
      alertMessage.clearCookie("alert-message-accepted");
    }
    
  }   
}

alertMessage.Init();