using System;
using System.Web.UI.WebControls;
using NewHireCompanyManager.Data;

namespace NewHireCompanyManager
{
    public partial class Default : System.Web.UI.Page
    {
        private readonly CompanyRepository _repository = new CompanyRepository();

        protected void Page_Load(object sender, EventArgs e)
        {
            if (!IsPostBack)
            {
                BindCompanies();
            }
        }

        protected void CreateNewButton_Click(object sender, EventArgs e)
        {
            Response.Redirect("~/NewCompany.aspx");
        }

        protected void CompanyGrid_PageIndexChanged(object source, DataGridPageChangedEventArgs e)
        {
            CompanyGrid.CurrentPageIndex = e.NewPageIndex;
            BindCompanies();
        }

        protected void CompanyGrid_ItemCommand(object source, DataGridCommandEventArgs e)
        {
            var companyIdentifier = Convert.ToString(e.CommandArgument);

            if (e.CommandName == "EditCompany")
            {
                Response.Redirect("~/NewCompany.aspx?id=" + Server.UrlEncode(companyIdentifier));
            }

            if (e.CommandName == "DeleteCompany")
            {
                try
                {
                    _repository.DeleteCompany(companyIdentifier);
                    ShowMessage("Company deleted.", false);
                    BindCompanies();
                }
                catch (Exception ex)
                {
                    ShowMessage("Unable to delete the company. " + ex.Message, true);
                }
            }
        }

        private void BindCompanies()
        {
            try
            {
                CompanyGrid.DataSource = _repository.GetCompanies();
                CompanyGrid.DataBind();
            }
            catch (Exception ex)
            {
                CompanyGrid.Visible = false;
                ShowMessage("The company database is not ready yet. Install SQL Server Express LocalDB, run Sql\\Database.sql in SSMS, then refresh this page. Details: " + ex.Message, true);
            }
        }

        private void ShowMessage(string message, bool isError)
        {
            MessageLabel.Text = message;
            MessageLabel.CssClass = isError ? "alert alert-danger" : "alert alert-info";
            MessageLabel.Visible = true;
        }
    }
}
