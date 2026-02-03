# API Key to create .oci/config + oci_api_key.pem to use instead of InstancePrincipal
resource "oci_identity_api_key" "oci_api_key" {
    provider = oci.home
    #Required
    key_value = trimspace(tls_private_key.ssh_key.public_key_pem)
    user_id = var.current_user_ocid
}