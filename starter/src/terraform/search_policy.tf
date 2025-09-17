variable no_policy { default=null }

resource "oci_identity_policy" "starter_search_policy" {
    count          = var.no_policy=="true" ? 0 : 1      
    provider       = oci.home    
    name           = "${var.prefix}-policy"
    description    = "${var.prefix} policy"
    compartment_id = local.lz_serv_cmp_ocid

    statements = [
        "allow any-user to manage objects in compartment id ${local.lz_serv_cmp_ocid} where request.principal.id='${join("", oci_functions_function.starter_fn_function.*.id)}'",
        "allow any-user to manage objects in compartment id ${local.lz_serv_cmp_ocid} where request.principal.id='${oci_functions_application.starter_fn_application.id}'",        
        "allow any-user to manage all-resources in compartment id ${local.lz_serv_cmp_ocid} where request.principal.id='${oci_core_instance.starter_bastion.id}'",
        "allow any-user to manage generative-ai-family in compartment id ${local.lz_serv_cmp_ocid} where request.principal.id='${oci_core_instance.starter_bastion.id}'",
        "allow any-user to manage stream-family in compartment id ${local.lz_serv_cmp_ocid} where request.principal.id='${oci_core_instance.starter_bastion.id}'",
        "allow any-user to manage genai-agent-family in compartment id ${local.lz_serv_cmp_ocid} where request.principal.id='${oci_core_instance.starter_bastion.id}'",
        "allow any-user to manage generative-ai-family in compartment id ${local.lz_serv_cmp_ocid} where request.principal.id='${data.oci_database_autonomous_database.starter_atp.autonomous_database_id}'",
        "allow any-user to manage genai-agent-family in compartment id ${local.lz_serv_cmp_ocid} where request.principal.id='${data.oci_database_autonomous_database.starter_atp.autonomous_database_id}'",
        "allow any-user to read object-family in compartment id ${local.lz_serv_cmp_ocid} where request.principal.id='${data.oci_database_autonomous_database.starter_atp.autonomous_database_id}'",
        "allow any-user to manage object-family in compartment id ${local.lz_serv_cmp_ocid} where ALL { request.principal.id='${data.oci_database_autonomous_database.starter_atp.autonomous_database_id}', request.permission = 'PAR_MANAGE' }",
        "allow any-user to manage database-tools-family in compartment id ${local.lz_serv_cmp_ocid} where request.principal.id='${oci_generative_ai_agent_agent.starter_agent.id}'",
        "allow any-user to read secret-bundle in compartment id ${local.lz_serv_cmp_ocid} where request.principal.id='${oci_generative_ai_agent_agent.starter_agent.id}'"
    ]
}

