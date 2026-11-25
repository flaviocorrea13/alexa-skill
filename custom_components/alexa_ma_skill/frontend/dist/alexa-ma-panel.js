const e=globalThis,t=e.ShadowRoot&&(void 0===e.ShadyCSS||e.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,s=Symbol(),i=new WeakMap;let r=class{constructor(e,t,i){if(this._$cssResult$=!0,i!==s)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o;const s=this.t;if(t&&void 0===e){const t=void 0!==s&&1===s.length;t&&(e=i.get(s)),void 0===e&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),t&&i.set(s,e))}return e}toString(){return this.cssText}};const n=(e,...t)=>{const i=1===e.length?e[0]:t.reduce((t,s,i)=>t+(e=>{if(!0===e._$cssResult$)return e.cssText;if("number"==typeof e)return e;throw Error("Value passed to 'css' function must be a 'css' function result: "+e+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(s)+e[i+1],e[0]);return new r(i,e,s)},a=t?e=>e:e=>e instanceof CSSStyleSheet?(e=>{let t="";for(const s of e.cssRules)t+=s.cssText;return(e=>new r("string"==typeof e?e:e+"",void 0,s))(t)})(e):e,{is:o,defineProperty:l,getOwnPropertyDescriptor:d,getOwnPropertyNames:h,getOwnPropertySymbols:c,getPrototypeOf:_}=Object,u=globalThis,p=u.trustedTypes,g=p?p.emptyScript:"",f=u.reactiveElementPolyfillSupport,v=(e,t)=>e,$={toAttribute(e,t){switch(t){case Boolean:e=e?g:null;break;case Object:case Array:e=null==e?e:JSON.stringify(e)}return e},fromAttribute(e,t){let s=e;switch(t){case Boolean:s=null!==e;break;case Number:s=null===e?null:Number(e);break;case Object:case Array:try{s=JSON.parse(e)}catch(e){s=null}}return s}},m=(e,t)=>!o(e,t),y={attribute:!0,type:String,converter:$,reflect:!1,useDefault:!1,hasChanged:m};Symbol.metadata??=Symbol("metadata"),u.litPropertyMetadata??=new WeakMap;let b=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=y){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){const s=Symbol(),i=this.getPropertyDescriptor(e,s,t);void 0!==i&&l(this.prototype,e,i)}}static getPropertyDescriptor(e,t,s){const{get:i,set:r}=d(this.prototype,e)??{get(){return this[t]},set(e){this[t]=e}};return{get:i,set(t){const n=i?.call(this);r?.call(this,t),this.requestUpdate(e,n,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??y}static _$Ei(){if(this.hasOwnProperty(v("elementProperties")))return;const e=_(this);e.finalize(),void 0!==e.l&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(v("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(v("properties"))){const e=this.properties,t=[...h(e),...c(e)];for(const s of t)this.createProperty(s,e[s])}const e=this[Symbol.metadata];if(null!==e){const t=litPropertyMetadata.get(e);if(void 0!==t)for(const[e,s]of t)this.elementProperties.set(e,s)}this._$Eh=new Map;for(const[e,t]of this.elementProperties){const s=this._$Eu(e,t);void 0!==s&&this._$Eh.set(s,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const t=[];if(Array.isArray(e)){const s=new Set(e.flat(1/0).reverse());for(const e of s)t.unshift(a(e))}else void 0!==e&&t.push(a(e));return t}static _$Eu(e,t){const s=t.attribute;return!1===s?void 0:"string"==typeof s?s:"string"==typeof e?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),void 0!==this.renderRoot&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){const e=new Map,t=this.constructor.elementProperties;for(const s of t.keys())this.hasOwnProperty(s)&&(e.set(s,this[s]),delete this[s]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const s=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((s,i)=>{if(t)s.adoptedStyleSheets=i.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(const t of i){const i=document.createElement("style"),r=e.litNonce;void 0!==r&&i.setAttribute("nonce",r),i.textContent=t.cssText,s.appendChild(i)}})(s,this.constructor.elementStyles),s}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,s){this._$AK(e,s)}_$ET(e,t){const s=this.constructor.elementProperties.get(e),i=this.constructor._$Eu(e,s);if(void 0!==i&&!0===s.reflect){const r=(void 0!==s.converter?.toAttribute?s.converter:$).toAttribute(t,s.type);this._$Em=e,null==r?this.removeAttribute(i):this.setAttribute(i,r),this._$Em=null}}_$AK(e,t){const s=this.constructor,i=s._$Eh.get(e);if(void 0!==i&&this._$Em!==i){const e=s.getPropertyOptions(i),r="function"==typeof e.converter?{fromAttribute:e.converter}:void 0!==e.converter?.fromAttribute?e.converter:$;this._$Em=i;const n=r.fromAttribute(t,e.type);this[i]=n??this._$Ej?.get(i)??n,this._$Em=null}}requestUpdate(e,t,s,i=!1,r){if(void 0!==e){const n=this.constructor;if(!1===i&&(r=this[e]),s??=n.getPropertyOptions(e),!((s.hasChanged??m)(r,t)||s.useDefault&&s.reflect&&r===this._$Ej?.get(e)&&!this.hasAttribute(n._$Eu(e,s))))return;this.C(e,t,s)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(e,t,{useDefault:s,reflect:i,wrapped:r},n){s&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,n??t??this[e]),!0!==r||void 0!==n)||(this._$AL.has(e)||(this.hasUpdated||s||(t=void 0),this._$AL.set(e,t)),!0===i&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}const e=this.scheduleUpdate();return null!=e&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[e,t]of this._$Ep)this[e]=t;this._$Ep=void 0}const e=this.constructor.elementProperties;if(e.size>0)for(const[t,s]of e){const{wrapped:e}=s,i=this[t];!0!==e||this._$AL.has(t)||void 0===i||this.C(t,void 0,s,i)}}let e=!1;const t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(e=>e.hostUpdate?.()),this.update(t)):this._$EM()}catch(t){throw e=!1,this._$EM(),t}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(e){}firstUpdated(e){}};b.elementStyles=[],b.shadowRootOptions={mode:"open"},b[v("elementProperties")]=new Map,b[v("finalized")]=new Map,f?.({ReactiveElement:b}),(u.reactiveElementVersions??=[]).push("2.1.2");const A=globalThis,w=e=>e,x=A.trustedTypes,S=x?x.createPolicy("lit-html",{createHTML:e=>e}):void 0,E="$lit$",k=`lit$${Math.random().toFixed(9).slice(2)}$`,C="?"+k,P=`<${C}>`,R=document,N=()=>R.createComment(""),T=e=>null===e||"object"!=typeof e&&"function"!=typeof e,M=Array.isArray,O="[ \t\n\f\r]",U=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,H=/-->/g,D=/>/g,I=RegExp(`>|${O}(?:([^\\s"'>=/]+)(${O}*=${O}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),z=/'/g,L=/"/g,j=/^(?:script|style|textarea|title)$/i,B=(e,...t)=>({_$litType$:1,strings:e,values:t}),W=Symbol.for("lit-noChange"),V=Symbol.for("lit-nothing"),F=new WeakMap,q=R.createTreeWalker(R,129);function J(e,t){if(!M(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==S?S.createHTML(t):t}const K=(e,t)=>{const s=e.length-1,i=[];let r,n=2===t?"<svg>":3===t?"<math>":"",a=U;for(let t=0;t<s;t++){const s=e[t];let o,l,d=-1,h=0;for(;h<s.length&&(a.lastIndex=h,l=a.exec(s),null!==l);)h=a.lastIndex,a===U?"!--"===l[1]?a=H:void 0!==l[1]?a=D:void 0!==l[2]?(j.test(l[2])&&(r=RegExp("</"+l[2],"g")),a=I):void 0!==l[3]&&(a=I):a===I?">"===l[0]?(a=r??U,d=-1):void 0===l[1]?d=-2:(d=a.lastIndex-l[2].length,o=l[1],a=void 0===l[3]?I:'"'===l[3]?L:z):a===L||a===z?a=I:a===H||a===D?a=U:(a=I,r=void 0);const c=a===I&&e[t+1].startsWith("/>")?" ":"";n+=a===U?s+P:d>=0?(i.push(o),s.slice(0,d)+E+s.slice(d)+k+c):s+k+(-2===d?t:c)}return[J(e,n+(e[s]||"<?>")+(2===t?"</svg>":3===t?"</math>":"")),i]};class Z{constructor({strings:e,_$litType$:t},s){let i;this.parts=[];let r=0,n=0;const a=e.length-1,o=this.parts,[l,d]=K(e,t);if(this.el=Z.createElement(l,s),q.currentNode=this.el.content,2===t||3===t){const e=this.el.content.firstChild;e.replaceWith(...e.childNodes)}for(;null!==(i=q.nextNode())&&o.length<a;){if(1===i.nodeType){if(i.hasAttributes())for(const e of i.getAttributeNames())if(e.endsWith(E)){const t=d[n++],s=i.getAttribute(e).split(k),a=/([.?@])?(.*)/.exec(t);o.push({type:1,index:r,name:a[2],strings:s,ctor:"."===a[1]?ee:"?"===a[1]?te:"@"===a[1]?se:X}),i.removeAttribute(e)}else e.startsWith(k)&&(o.push({type:6,index:r}),i.removeAttribute(e));if(j.test(i.tagName)){const e=i.textContent.split(k),t=e.length-1;if(t>0){i.textContent=x?x.emptyScript:"";for(let s=0;s<t;s++)i.append(e[s],N()),q.nextNode(),o.push({type:2,index:++r});i.append(e[t],N())}}}else if(8===i.nodeType)if(i.data===C)o.push({type:2,index:r});else{let e=-1;for(;-1!==(e=i.data.indexOf(k,e+1));)o.push({type:7,index:r}),e+=k.length-1}r++}}static createElement(e,t){const s=R.createElement("template");return s.innerHTML=e,s}}function Y(e,t,s=e,i){if(t===W)return t;let r=void 0!==i?s._$Co?.[i]:s._$Cl;const n=T(t)?void 0:t._$litDirective$;return r?.constructor!==n&&(r?._$AO?.(!1),void 0===n?r=void 0:(r=new n(e),r._$AT(e,s,i)),void 0!==i?(s._$Co??=[])[i]=r:s._$Cl=r),void 0!==r&&(t=Y(e,r._$AS(e,t.values),r,i)),t}class G{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:t},parts:s}=this._$AD,i=(e?.creationScope??R).importNode(t,!0);q.currentNode=i;let r=q.nextNode(),n=0,a=0,o=s[0];for(;void 0!==o;){if(n===o.index){let t;2===o.type?t=new Q(r,r.nextSibling,this,e):1===o.type?t=new o.ctor(r,o.name,o.strings,this,e):6===o.type&&(t=new ie(r,this,e)),this._$AV.push(t),o=s[++a]}n!==o?.index&&(r=q.nextNode(),n++)}return q.currentNode=R,i}p(e){let t=0;for(const s of this._$AV)void 0!==s&&(void 0!==s.strings?(s._$AI(e,s,t),t+=s.strings.length-2):s._$AI(e[t])),t++}}class Q{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,s,i){this.type=2,this._$AH=V,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode;const t=this._$AM;return void 0!==t&&11===e?.nodeType&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=Y(this,e,t),T(e)?e===V||null==e||""===e?(this._$AH!==V&&this._$AR(),this._$AH=V):e!==this._$AH&&e!==W&&this._(e):void 0!==e._$litType$?this.$(e):void 0!==e.nodeType?this.T(e):(e=>M(e)||"function"==typeof e?.[Symbol.iterator])(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==V&&T(this._$AH)?this._$AA.nextSibling.data=e:this.T(R.createTextNode(e)),this._$AH=e}$(e){const{values:t,_$litType$:s}=e,i="number"==typeof s?this._$AC(e):(void 0===s.el&&(s.el=Z.createElement(J(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(t);else{const e=new G(i,this),s=e.u(this.options);e.p(t),this.T(s),this._$AH=e}}_$AC(e){let t=F.get(e.strings);return void 0===t&&F.set(e.strings,t=new Z(e)),t}k(e){M(this._$AH)||(this._$AH=[],this._$AR());const t=this._$AH;let s,i=0;for(const r of e)i===t.length?t.push(s=new Q(this.O(N()),this.O(N()),this,this.options)):s=t[i],s._$AI(r),i++;i<t.length&&(this._$AR(s&&s._$AB.nextSibling,i),t.length=i)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){const t=w(e).nextSibling;w(e).remove(),e=t}}setConnected(e){void 0===this._$AM&&(this._$Cv=e,this._$AP?.(e))}}class X{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,s,i,r){this.type=1,this._$AH=V,this._$AN=void 0,this.element=e,this.name=t,this._$AM=i,this.options=r,s.length>2||""!==s[0]||""!==s[1]?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=V}_$AI(e,t=this,s,i){const r=this.strings;let n=!1;if(void 0===r)e=Y(this,e,t,0),n=!T(e)||e!==this._$AH&&e!==W,n&&(this._$AH=e);else{const i=e;let a,o;for(e=r[0],a=0;a<r.length-1;a++)o=Y(this,i[s+a],t,a),o===W&&(o=this._$AH[a]),n||=!T(o)||o!==this._$AH[a],o===V?e=V:e!==V&&(e+=(o??"")+r[a+1]),this._$AH[a]=o}n&&!i&&this.j(e)}j(e){e===V?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}}class ee extends X{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===V?void 0:e}}class te extends X{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==V)}}class se extends X{constructor(e,t,s,i,r){super(e,t,s,i,r),this.type=5}_$AI(e,t=this){if((e=Y(this,e,t,0)??V)===W)return;const s=this._$AH,i=e===V&&s!==V||e.capture!==s.capture||e.once!==s.once||e.passive!==s.passive,r=e!==V&&(s===V||i);i&&this.element.removeEventListener(this.name,this,s),r&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}}class ie{constructor(e,t,s){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(e){Y(this,e)}}const re=A.litHtmlPolyfillSupport;re?.(Z,Q),(A.litHtmlVersions??=[]).push("3.3.3");const ne=globalThis;class ae extends b{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){const t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=((e,t,s)=>{const i=s?.renderBefore??t;let r=i._$litPart$;if(void 0===r){const e=s?.renderBefore??null;i._$litPart$=r=new Q(t.insertBefore(N(),e),e,void 0,s??{})}return r._$AI(e),r})(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return W}}ae._$litElement$=!0,ae.finalized=!0,ne.litElementHydrateSupport?.({LitElement:ae});const oe=ne.litElementPolyfillSupport;oe?.({LitElement:ae}),(ne.litElementVersions??=[]).push("4.2.2");const le="alexa_ma_skill";class de{hass;constructor(e){this.hass=e}entries(){return this.hass.connection.sendMessagePromise({type:`${le}/entries`})}overview(e){return this.hass.connection.sendMessagePromise(this.withEntry(`${le}/overview`,e))}refresh(e){return this.hass.connection.sendMessagePromise(this.withEntry(`${le}/refresh`,e))}withEntry(e,t){const s={type:e};return t&&(s.entry_id=t),s}}const he={title:"Alexa MA",subtitle:"Administração da integração e do add-on",loading:"Carregando...",refresh:"Atualizar",refreshing:"Atualizando...",entry:"Configuração",last_update:"Última atualização",never:"Nunca",integration:"Integração",addon:"Add-on",music_assistant:"Music Assistant",alexa:"Amazon Alexa",checklist:"Checklist",connected:"Conectado",stale:"Dados desatualizados",integration_not_loaded:"Integração não carregada",addon_not_found:"Add-on não encontrado",addon_stopped:"Add-on parado",ma_unavailable:"Music Assistant indisponível",config_incomplete:"Configuração incompleta",error:"Erro",unknown:"Desconhecido",yes:"Sim",no:"Não",version:"Versão",state:"Estado",reachable:"Alcançável",installed:"Instalado",running:"Em execução",configured:"Configurado",skill_id:"Skill ID (mascarado)",detected_skill_id:"Skill ID detectado",skill_id_matches:"Skill ID confere",skill_id_suggested:"O Skill ID detectado difere do configurado. Revise a configuração.",stream:"Stream",stream_ok:"Stream HTTPS",next_step:"Próxima etapa",progress:"Progresso",warnings:"Avisos",load_failed:"Não foi possível carregar o painel.",refresh_failed:"Não foi possível atualizar os dados.",no_entries:"Nenhuma configuração do Alexa MA está carregada.",recovery_failed:"Não foi possível recarregar a lista de configurações.",retry:"Tentar novamente",select_entry:"Selecione a configuração",addon_not_available:"Supervisor indisponível",status_details:"Detalhes"},ce={title:"Alexa MA",subtitle:"Integration and add-on administration",loading:"Loading...",refresh:"Refresh",refreshing:"Refreshing...",entry:"Configuration",last_update:"Last update",never:"Never",integration:"Integration",addon:"Add-on",music_assistant:"Music Assistant",alexa:"Amazon Alexa",checklist:"Checklist",connected:"Connected",stale:"Data is stale",integration_not_loaded:"Integration not loaded",addon_not_found:"Add-on not found",addon_stopped:"Add-on stopped",ma_unavailable:"Music Assistant unavailable",config_incomplete:"Configuration incomplete",error:"Error",unknown:"Unknown",yes:"Yes",no:"No",version:"Version",state:"State",reachable:"Reachable",installed:"Installed",running:"Running",configured:"Configured",skill_id:"Skill ID (masked)",detected_skill_id:"Detected Skill ID",skill_id_matches:"Skill ID matches",skill_id_suggested:"The detected Skill ID differs from the configured one. Review the configuration.",stream:"Stream",stream_ok:"HTTPS stream",next_step:"Next step",progress:"Progress",warnings:"Warnings",load_failed:"Could not load the panel.",refresh_failed:"Could not refresh the data.",no_entries:"No Alexa MA configuration is loaded.",recovery_failed:"Could not reload the list of configurations.",retry:"Try again",select_entry:"Select configuration",addon_not_available:"Supervisor unavailable",status_details:"Details"},_e=new Set(["connected","addon_not_found","addon_stopped","ma_unavailable","config_incomplete","error"]);function ue(e,t){if(t)return{state:"error",stale:!1,backendState:null};if(null===e)return{state:"integration_not_loaded",stale:!1,backendState:null};const s=_e.has(e.state)?e.state:"error";return"connected"===s&&e.stale?{state:"stale",stale:!0,backendState:s}:{state:s,stale:e.stale,backendState:s}}function pe(e,t){return!t&&function(e){return"object"==typeof e&&null!==e&&"entry_not_found"===e.code}(e)}const ge="alexa-ma-panel";class fe extends ae{static properties={hass:{attribute:!1},narrow:{attribute:!1},_loading:{state:!0},_refreshing:{state:!0},_entries:{state:!0},_selected:{state:!0},_overview:{state:!0},_error:{state:!0},_updatedAt:{state:!0}};hass;narrow=!1;_api=null;_loading=!0;_refreshing=!1;_entries=[];_selected=null;_overview=null;_error=null;_updatedAt=null;_recovering=!1;_recoveryFailed=!1;connectedCallback(){super.connectedCallback(),this._load()}updated(e){e.has("hass")&&this.hass&&!this._api&&this._load()}async _load(){if(this.hass){this._loading=!0,this._error=null,this._recoveryFailed=!1,this._api=new de(this.hass);try{const e=await this._api.entries();this._entries=e.entries,this._selectInitial(e),this._selected?await this._loadOverview():this._overview=null}catch(e){pe(e,this._recovering)?await this._runRecovery(this._selected):(this._error=this._label("load_failed"),this._overview=null)}finally{this._loading=!1}}}_selectInitial(e){this._selected&&this._entries.some(e=>e.entry_id===this._selected)||(this._selected=e.default_entry_id??this._entries[0]?.entry_id??null,this._overview=null,this._updatedAt=null)}async _loadOverview(){const e=this._selected;if(this._api&&e)try{const t=await this._api.overview(e);if(this._selected!==e)return;this._overview=t,this._updatedAt=this._formatTime(t.generated_at),this._error=null,this._recoveryFailed=!1}catch(t){if(this._selected!==e)return;if(pe(t,this._recovering))return void await this._runRecovery(e);throw t}}_applyRecoveryResult(e){this._entries=e.entries,this._selected=e.selected,this._overview=e.overview,this._updatedAt=e.overview?this._formatTime(e.overview.generated_at):null,this._error=e.error?this._label(e.error):null,this._recoveryFailed=null!==e.error}async _runRecovery(e){if(this._api&&!this._recovering){this._recovering=!0;try{const t=await async function(e,t,s=()=>!0){let i;try{i=await e.entries()}catch{return s()?{stale:!1,entries:[],selected:null,overview:null,error:"recovery_failed"}:{stale:!0,entries:[],selected:null,overview:null,error:null}}if(!s())return{stale:!0,entries:[],selected:null,overview:null,error:null};if(null!==t&&i.entries.some(e=>e.entry_id===t))return{stale:!1,entries:i.entries,selected:t,overview:null,error:"recovery_failed"};const r=function(e){return e.default_entry_id??e.entries[0]?.entry_id??null}(i);if(null===r)return{stale:!1,entries:i.entries,selected:null,overview:null,error:null};try{const t=await e.overview(r);return s()?{stale:!1,entries:i.entries,selected:r,overview:t,error:null}:{stale:!0,entries:[],selected:null,overview:null,error:null}}catch{return s()?{stale:!1,entries:i.entries,selected:r,overview:null,error:"recovery_failed"}:{stale:!0,entries:[],selected:null,overview:null,error:null}}}(this._api,e,()=>this._selected===e);if(t.stale)return;this._applyRecoveryResult(t)}finally{this._recovering=!1}}}async _refresh(){const e=this._selected;if(this._api&&e&&!this._refreshing){this._refreshing=!0,this._error=null,this._recoveryFailed=!1;try{const t=await this._api.refresh(e);if(this._selected!==e)return;this._overview=t.overview,this._updatedAt=this._formatTime(t.overview.generated_at)}catch(t){if(this._selected!==e)return;pe(t,this._recovering)?await this._runRecovery(e):this._error=this._label("refresh_failed")}finally{this._refreshing=!1}}}async _changeEntry(e){const t=e.target;this._selected=t.value||null,this._overview=null,this._loading=!0,this._recoveryFailed=!1;try{await this._loadOverview()}catch(e){pe(e,this._recovering)?await this._runRecovery(this._selected):this._error=this._label("load_failed")}finally{this._loading=!1}}_label(e){return function(e,t){return("pt"===e?he:ce)[t]??t}((t=this.hass?.language,t?.toLowerCase().startsWith("pt")?"pt":"en"),e);var t}_formatTime(e){if(!e)return this._label("never");const t=new Date(e);return Number.isNaN(t.getTime())?this._label("unknown"):t.toLocaleString()}_stateLabel(e){return this._label(e)}_value(e){return null==e||""===e?this._label("unknown"):"boolean"==typeof e?this._label(e?"yes":"no"):String(e)}_renderOverview(e){const t=ue(e,this._error),s=e.checklist;return B`
            <div class="status-line">
                <span class="badge ${t.state}">${this._stateLabel(t.state)}</span>
                ${t.stale?B`<span class="stale">${this._label("stale")}</span>`:V}
            </div>
            ${this._error?B`<div class="error" role="alert">${this._error}</div>`:V}
            <div class="grid">
                <section class="card">
                    <h2>${this._label("integration")}</h2>
                    <dl>
                        <dt>${this._label("version")}</dt>
                        <dd>${this._value(e.integration.version)}</dd>
                        <dt>${this._label("reachable")}</dt>
                        <dd>${this._value(e.integration.reachable)}</dd>
                    </dl>
                </section>
                <section class="card">
                    <h2>${this._label("addon")}</h2>
                    <dl>
                        <dt>${this._label("installed")}</dt>
                        <dd>${this._value(e.addon.installed)}</dd>
                        <dt>${this._label("running")}</dt>
                        <dd>${this._value(e.addon.running)}</dd>
                        <dt>${this._label("version")}</dt>
                        <dd>${this._value(e.addon.version)}</dd>
                        <dt>${this._label("state")}</dt>
                        <dd>${this._value(e.addon.state)}</dd>
                    </dl>
                </section>
                <section class="card">
                    <h2>${this._label("music_assistant")}</h2>
                    <dl>
                        <dt>${this._label("configured")}</dt>
                        <dd>${this._value(e.music_assistant.configured)}</dd>
                        <dt>${this._label("state")}</dt>
                        <dd>${this._value(e.music_assistant.level)}</dd>
                        <dt>${this._label("stream")}</dt>
                        <dd>${this._value(e.music_assistant.stream_present)}</dd>
                        <dt>${this._label("stream_ok")}</dt>
                        <dd>${this._value(e.music_assistant.stream_https_ok)}</dd>
                    </dl>
                </section>
                <section class="card">
                    <h2>${this._label("alexa")}</h2>
                    <dl>
                        <dt>${this._label("configured")}</dt>
                        <dd>${this._value(e.alexa.configured)}</dd>
                        <dt>${this._label("state")}</dt>
                        <dd>${this._value(e.alexa.skill_linked)}</dd>
                        <dt>${this._label("skill_id")}</dt>
                        <dd class="mono">
                            ${this._value(e.alexa.configured_skill_id_masked)}
                        </dd>
                        <dt>${this._label("detected_skill_id")}</dt>
                        <dd class="mono">
                            ${this._value(e.alexa.detected_skill_id_masked)}
                        </dd>
                        <dt>${this._label("skill_id_matches")}</dt>
                        <dd>${this._value(e.alexa.skill_id_matches)}</dd>
                    </dl>
                    ${e.alexa.skill_id_suggested?B`<p class="hint">
                              ${this._label("skill_id_suggested")}
                          </p>`:V}
                </section>
                <section class="card wide">
                    <h2>${this._label("checklist")}</h2>
                    ${s?B`
                              <p class="progress">
                                  ${this._label("progress")}:
                                  ${s.done}/${s.applicable}
                                  (${s.percent}%)
                              </p>
                              <p>
                                  ${this._label("next_step")}:
                                  ${this._value(s.next_step_title)}
                              </p>
                          `:B`<p>${this._label("unknown")}</p>`}
                </section>
            </div>
            ${e.warnings.length?B`
                      <section class="card wide">
                          <h2>${this._label("warnings")}</h2>
                          <ul>
                              ${e.warnings.map(e=>B`<li>${e}</li>`)}
                          </ul>
                      </section>
                  `:V}
            <p class="updated">
                ${this._label("last_update")}: ${this._updatedAt??this._label("never")}
            </p>
        `}_renderEmptyState(){return this._recoveryFailed?B`
                <div class="empty">
                    <p>${this._label("recovery_failed")}</p>
                    <button
                        class="refresh"
                        ?disabled=${this._recovering}
                        @click=${()=>{this._runRecovery(this._selected)}}
                    >
                        ${this._recovering?this._label("loading"):this._label("retry")}
                    </button>
                </div>
            `:B`
            <div class="empty">
                <p>${this._label("no_entries")}</p>
                ${this._error?B`<p class="error">${this._error}</p>`:V}
            </div>
        `}render(){const e=this._loading&&!this._overview?{state:"loading",stale:!1,backendState:null}:ue(this._overview,this._error);return B`
            <div class="page">
                <header class="header">
                    <div>
                        <h1>${this._label("title")}</h1>
                        <p>${this._label("subtitle")}</p>
                    </div>
                    <button
                        class="refresh"
                        ?disabled=${this._refreshing||!this._selected}
                        @click=${()=>{this._refresh()}}
                    >
                        ${this._refreshing?this._label("refreshing"):this._label("refresh")}
                    </button>
                </header>
                ${this._entries.length>1?B`
                          <label class="entry-select">
                              ${this._label("select_entry")}
                              <select
                                  .value=${this._selected??""}
                                  @change=${e=>{this._changeEntry(e)}}
                              >
                                  ${this._entries.map(e=>B`
                                          <option value=${e.entry_id}>
                                              ${e.title}
                                          </option>
                                      `)}
                              </select>
                          </label>
                      `:V}
                ${"loading"===e.state?B`<div class="loading" role="status">
                          <span class="spinner"></span>
                          ${this._label("loading")}
                      </div>`:this._overview?this._renderOverview(this._overview):this._renderEmptyState()}
            </div>
        `}static styles=n`
        :host {
            display: block;
            padding: 16px;
            color: var(--primary-text-color);
        }
        .page {
            max-width: 1100px;
            margin: 0 auto;
        }
        .header {
            display: flex;
            gap: 16px;
            align-items: flex-start;
            justify-content: space-between;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }
        h1 {
            margin: 0;
            font-size: 1.8rem;
        }
        h2 {
            margin: 0 0 8px;
            font-size: 1rem;
        }
        .header p {
            margin: 4px 0 0;
            color: var(--secondary-text-color);
        }
        .refresh {
            border: 0;
            border-radius: 6px;
            padding: 10px 16px;
            cursor: pointer;
            color: var(--text-primary-color);
            background: var(--primary-color);
            font: inherit;
        }
        .refresh:disabled {
            opacity: 0.55;
            cursor: default;
        }
        .entry-select {
            display: flex;
            flex-direction: column;
            gap: 4px;
            margin-bottom: 16px;
            max-width: 420px;
        }
        select {
            padding: 8px;
            border-radius: 6px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
        }
        .status-line {
            display: flex;
            gap: 10px;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }
        .badge,
        .stale {
            display: inline-block;
            border-radius: 999px;
            padding: 6px 12px;
            font-weight: 600;
        }
        .badge.connected {
            background: var(--success-color);
            color: #fff;
        }
        .badge.error,
        .badge.addon_not_found,
        .badge.addon_stopped,
        .badge.ma_unavailable {
            background: var(--error-color);
            color: #fff;
        }
        .badge.config_incomplete,
        .badge.stale {
            background: var(--warning-color);
            color: #000;
        }
        .stale {
            background: var(--warning-color);
            color: #000;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
            gap: 12px;
        }
        .card {
            border: 1px solid var(--divider-color);
            border-radius: 10px;
            padding: 14px;
            background: var(--card-background-color);
        }
        .card.wide {
            grid-column: 1 / -1;
        }
        dl {
            display: grid;
            grid-template-columns: 1fr auto;
            gap: 6px 14px;
            margin: 0;
        }
        dt {
            color: var(--secondary-text-color);
        }
        dd {
            margin: 0;
            text-align: right;
            overflow-wrap: anywhere;
        }
        .mono {
            font-family: var(--code-font-family, monospace);
            font-size: 0.9rem;
        }
        .hint {
            margin: 10px 0 0;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
        }
        .loading,
        .empty {
            display: flex;
            gap: 10px;
            align-items: center;
            padding: 24px;
            border: 1px dashed var(--divider-color);
            border-radius: 10px;
        }
        .spinner {
            width: 18px;
            height: 18px;
            border: 2px solid var(--divider-color);
            border-top-color: var(--primary-color);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        .error {
            margin: 12px 0;
            padding: 10px 12px;
            border-radius: 8px;
            background: var(--error-color);
            color: #fff;
        }
        .updated {
            margin-top: 16px;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
        }
        @keyframes spin {
            to {
                transform: rotate(360deg);
            }
        }
        @media (max-width: 600px) {
            :host {
                padding: 10px;
            }
            .header {
                align-items: stretch;
            }
            .refresh {
                width: 100%;
            }
        }
    `}customElements.get(ge)||customElements.define(ge,fe);export{fe as AlexaMaPanel};
