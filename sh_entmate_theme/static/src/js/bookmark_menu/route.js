/** @odoo-module **/

window.addEventListener("popstate", function () {
    console.log("URL changed:", window.location.href);
    myCustomMethod();
});

function myCustomMethod() {
    console.log("Executing custom logic...");
}

