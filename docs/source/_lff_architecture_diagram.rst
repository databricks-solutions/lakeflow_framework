.. raw:: html

   <figure class="lf-arch" aria-label="Lakeflow Framework architecture">
     <svg class="lf-arch__svg" viewBox="0 0 1000 560" width="840" role="img" xmlns="http://www.w3.org/2000/svg">
       <!-- Framework Bundle -->
       <rect class="lf-arch__panel lf-arch__panel--fw" x="20" y="20" width="470" height="360" rx="16"/>
       <path class="lf-arch__header lf-arch__header--fw" d="M22 36a14 14 0 0 1 14-14h438a14 14 0 0 1 14 14v46H22z"/>
       <g class="lf-arch__icon lf-arch__icon--fw lf-arch__icon--package" transform="translate(44,28) scale(1.55)">
         <path d="M3 8.2 12 3.5 21 8.2v9.6L12 22.5 3 17.8z"/>
         <path d="M12 13.2V22.5"/>
         <path d="M3 8.2 12 13.2 21 8.2"/>
         <path d="M7.2 5.9 16.8 10.9"/>
       </g>
       <text class="lf-arch__title" x="100" y="64" font-size="30">Framework Bundle</text>

       <rect class="lf-arch__card lf-arch__card--fw" x="44" y="108" width="422" height="96" rx="12"/>
       <g class="lf-arch__icon lf-arch__icon--fw lf-arch__icon--layers" transform="translate(64,124) scale(2.15)">
         <path d="M13 1.5 23.5 7.2 13 12.9 2.5 7.2Z"/>
         <path d="M2.5 11.2 13 16.9 23.5 11.2"/>
         <path d="M2.5 16.2 13 21.9 23.5 16.2"/>
       </g>
       <text class="lf-arch__card-title" x="148" y="150" font-size="24">Abstraction Layer</text>
       <text class="lf-arch__card-sub" x="148" y="180" font-size="17">Data Flow Spec &#183; Patterns &#183; Features</text>

       <line class="lf-arch__arrow-line" x1="255" y1="204" x2="255" y2="228"/>
       <polygon class="lf-arch__arrow-head" points="255,238 245,222 265,222"/>

       <rect class="lf-arch__card lf-arch__card--fw" x="44" y="244" width="422" height="96" rx="12"/>
       <g class="lf-arch__icon lf-arch__icon--fw lf-arch__icon--window" transform="translate(64,262) scale(2.15)">
         <rect x="1" y="1" width="24" height="20" rx="2.5"/>
         <path d="M1 7.5h24"/>
         <circle class="lf-arch__icon-dot" cx="5" cy="4.2" r="1.15"/>
         <circle class="lf-arch__icon-dot" cx="8.8" cy="4.2" r="1.15"/>
         <circle class="lf-arch__icon-dot" cx="12.6" cy="4.2" r="1.15"/>
         <path d="M9.2 11.2 6.2 14.2 9.2 17.2"/>
         <path d="M16.8 11.2 19.8 14.2 16.8 17.2"/>
         <path d="M14.2 10.8 11.8 17.6"/>
       </g>
       <text class="lf-arch__card-title" x="148" y="286" font-size="24">SDP Wrapper</text>
       <text class="lf-arch__card-sub" x="148" y="316" font-size="17">Spark Declarative Pipelines APIs</text>

       <rect class="lf-arch__frame lf-arch__frame--fw" x="20" y="20" width="470" height="360" rx="16"/>

       <!-- Pipeline Bundle (green) -->
       <rect class="lf-arch__panel lf-arch__panel--pl" x="510" y="20" width="470" height="360" rx="16"/>
       <path class="lf-arch__header lf-arch__header--pl" d="M512 36a14 14 0 0 1 14-14h438a14 14 0 0 1 14 14v46H512z"/>
       <g class="lf-arch__icon lf-arch__icon--pl lf-arch__icon--flow" transform="translate(534,30) scale(1.7)">
         <rect x="8" y="1" width="9" height="9" rx="1.5"/>
         <rect x="1" y="15" width="9" height="9" rx="1.5"/>
         <rect x="16" y="15" width="9" height="9" rx="1.5"/>
         <path d="M12.5 10v3M12.5 13H5.5M12.5 13h7"/>
       </g>
       <text class="lf-arch__title" x="590" y="64" font-size="30">Pipeline Bundle</text>

       <rect class="lf-arch__card lf-arch__card--pl" x="534" y="108" width="422" height="96" rx="12"/>
       <g class="lf-arch__icon lf-arch__icon--pl lf-arch__icon--gear" transform="translate(554,124) scale(2.15)">
         <path d="M14.4 3.1h-2.8l-.4 2.1c-.55.14-1.07.36-1.55.64L7.7 4.7 5.7 6.7l1.14 1.95c-.28.48-.5 1-.64 1.55L4.1 10.6v2.8l2.1.4c.14.55.36 1.07.64 1.55L5.7 17.3l2 2 1.95-1.14c.48.28 1 .5 1.55.64l.4 2.1h2.8l.4-2.1c.55-.14 1.07-.36 1.55-.64l1.95 1.14 2-2-1.14-1.95c.28-.48.5-1 .64-1.55l2.1-.4v-2.8l-2.1-.4c-.14-.55-.36-1.07-.64-1.55L20.3 6.7l-2-2-1.95 1.14c-.48-.28-1-.5-1.55-.64l-.4-2.1z"/>
         <circle cx="13" cy="13" r="3.4"/>
       </g>
       <text class="lf-arch__card-title" x="638" y="150" font-size="24">Resource definitions</text>
       <text class="lf-arch__card-sub" x="638" y="180" font-size="17">Pipelines &#183; Jobs</text>

       <rect class="lf-arch__card lf-arch__card--pl" x="534" y="244" width="422" height="96" rx="12"/>
       <g class="lf-arch__icon lf-arch__icon--pl lf-arch__icon--doc" transform="translate(554,258) scale(2.15)">
         <path d="M7 2h9l6 6v14a2.5 2.5 0 0 1-2.5 2.5H7A2.5 2.5 0 0 1 4.5 22V4.5A2.5 2.5 0 0 1 7 2z"/>
         <path d="M16 2v6h6"/>
         <path d="M8.5 13h9M8.5 17h9M8.5 21h6"/>
       </g>
       <text class="lf-arch__card-title" x="638" y="286" font-size="24">Data Flow Specs</text>
       <text class="lf-arch__card-sub" x="638" y="316" font-size="17">Metadata Per Data Flow &#183; src/dataflows/</text>

       <rect class="lf-arch__frame lf-arch__frame--pl" x="510" y="20" width="470" height="360" rx="16"/>

       <!-- DABS Foundation (Databricks brand) -->
       <rect class="lf-arch__panel lf-arch__panel--dabs" x="20" y="408" width="960" height="128" rx="16"/>
       <g class="lf-arch__icon lf-arch__icon--dabs lf-arch__icon--databricks" transform="translate(52,434) scale(2.35)" aria-label="Databricks">
         <!-- Simple Icons Databricks mark (CC0) -->
         <path d="M.95 14.184 12 20.403l9.919-5.55v2.21L12 22.662l-10.484-5.96-.565.308v.77L12 24l11.05-6.218v-4.317l-.515-.309L12 19.118l-9.867-5.653v-2.21L12 16.805l11.05-6.218V6.32l-.515-.308L12 11.974 2.647 6.681 12 1.388l7.76 4.368.668-.411v-.566L12 0 .95 6.27v.72L12 13.207l9.919-5.55v2.26L12 15.52 1.516 9.56l-.565.308Z"/>
       </g>
       <text class="lf-arch__title" x="150" y="470" font-size="30">DABS Foundation</text>
       <text class="lf-arch__card-sub" x="150" y="506" font-size="18">Declarative Automation Bundles</text>
       <rect class="lf-arch__frame lf-arch__frame--dabs" x="20" y="408" width="960" height="128" rx="16"/>
     </svg>
   </figure>
