using System;
using System.Collections.Generic;
using System.IO;
using System.Web.UI.WebControls;
using NewHireCompanyManager.Data;
using NewHireCompanyManager.Models;

namespace NewHireCompanyManager
{
    public partial class NewCompany : System.Web.UI.Page
    {
        private static readonly string[] ModuleNames =
        {
            "ABR",
            "ACA",
            "Accounts Payable",
            "Approve Profile Changes",
            "Benefits Portal",
            "Contracts",
            "Document Box",
            "E-Stubs",
            "Finance Repository",
            "Leave",
            "Name Change",
            "OnBoarding/Tasks",
            "Profile/Demographic",
            "Total Compensation",
            "Transportation",
            "W2 Processing"
        };

        private readonly CompanyRepository _repository = new CompanyRepository();

        protected bool IsEditMode
        {
            get { return !string.IsNullOrWhiteSpace(Request.QueryString["id"]); }
        }

        protected void Page_Load(object sender, EventArgs e)
        {
            if (!IsPostBack)
            {
                BindStates();
                BindModules();

                if (IsEditMode)
                {
                    LoadCompany(Request.QueryString["id"]);
                }
            }
        }

        protected void SaveButton_Click(object sender, EventArgs e)
        {
            if (!Page.IsValid)
            {
                return;
            }

            var company = BuildCompanyFromForm();
            try
            {
                _repository.SaveCompany(company, !IsEditMode);
                Response.Redirect("~/Default.aspx");
            }
            catch (Exception ex)
            {
                MessageLabel.CssClass = "alert alert-danger";
                MessageLabel.Text = "Unable to save the company. Make sure SQL Server LocalDB is installed and Sql\\Database.sql has been run. Details: " + ex.Message;
                MessageLabel.Visible = true;
            }
        }

        protected void CancelButton_Click(object sender, EventArgs e)
        {
            Response.Redirect("~/Default.aspx");
        }

        private void LoadCompany(string companyIdentifier)
        {
            Company company;

            try
            {
                company = _repository.GetCompany(companyIdentifier);
            }
            catch (Exception ex)
            {
                MessageLabel.CssClass = "alert alert-danger";
                MessageLabel.Text = "Unable to load the company. Details: " + ex.Message;
                MessageLabel.Visible = true;
                return;
            }

            if (company == null)
            {
                Response.Redirect("~/Default.aspx");
                return;
            }

            PageTitleLiteral.Text = "Edit Company";
            CompanyIdentifierTextBox.Text = company.CompanyIdentifier;
            CompanyIdentifierTextBox.ReadOnly = true;
            CompanyNameTextBox.Text = company.CompanyName;
            Address1TextBox.Text = company.Address1;
            Address2TextBox.Text = company.Address2;
            CityTextBox.Text = company.City;
            SelectListValue(StateDropDown, company.State);
            ZipTextBox.Text = company.Zip;
            PhoneNumberTextBox.Text = company.PhoneNumber;
            PrimaryContactTextBox.Text = company.PrimaryContact;
            EmailTextBox.Text = company.PointOfContactEmail;
            TaxIdTextBox.Text = company.TaxId;
            BankNameTextBox.Text = company.BankName;
            Form1099CheckBox.Checked = company.Form1099;
            WithholdingNumberTextBox.Text = company.WithholdingNumber;
            CountyTextBox.Text = company.County;

            if (!string.IsNullOrWhiteSpace(company.LogoFileName))
            {
                ExistingLogoLiteral.Text = "<p class=\"help-block\">Current file: " + Server.HtmlEncode(company.LogoFileName) + "</p>";
            }

            foreach (var module in company.Modules)
            {
                var item = ModulesCheckBoxList.Items.FindByValue(module.Name);
                if (item != null)
                {
                    item.Selected = module.IsEnabled;
                }
            }
        }

        private Company BuildCompanyFromForm()
        {
            var company = new Company
            {
                CompanyIdentifier = CompanyIdentifierTextBox.Text.Trim(),
                CompanyName = CompanyNameTextBox.Text.Trim(),
                Address1 = Address1TextBox.Text.Trim(),
                Address2 = Address2TextBox.Text.Trim(),
                City = CityTextBox.Text.Trim(),
                State = StateDropDown.SelectedValue,
                Zip = ZipTextBox.Text.Trim(),
                PhoneNumber = PhoneNumberTextBox.Text.Trim(),
                PrimaryContact = PrimaryContactTextBox.Text.Trim(),
                PointOfContactEmail = EmailTextBox.Text.Trim(),
                TaxId = TaxIdTextBox.Text.Trim(),
                BankName = BankNameTextBox.Text.Trim(),
                Form1099 = Form1099CheckBox.Checked,
                WithholdingNumber = WithholdingNumberTextBox.Text.Trim(),
                County = CountyTextBox.Text.Trim(),
                Modules = GetSelectedModules()
            };

            if (LogoUpload.HasFile)
            {
                using (var stream = LogoUpload.PostedFile.InputStream)
                using (var reader = new BinaryReader(stream))
                {
                    company.LogoFileName = Path.GetFileName(LogoUpload.FileName);
                    company.LogoContentType = LogoUpload.PostedFile.ContentType;
                    company.LogoBytes = reader.ReadBytes(LogoUpload.PostedFile.ContentLength);
                }
            }

            return company;
        }

        private IList<CompanyModule> GetSelectedModules()
        {
            var modules = new List<CompanyModule>();

            foreach (ListItem item in ModulesCheckBoxList.Items)
            {
                modules.Add(new CompanyModule
                {
                    Name = item.Value,
                    IsEnabled = item.Selected
                });
            }

            return modules;
        }

        private void BindModules()
        {
            ModulesCheckBoxList.Items.Clear();

            foreach (var moduleName in ModuleNames)
            {
                ModulesCheckBoxList.Items.Add(new ListItem(moduleName, moduleName));
            }
        }

        private void BindStates()
        {
            StateDropDown.Items.Clear();
            StateDropDown.Items.Add(new ListItem("-- Select --", string.Empty));

            string[] states =
            {
                "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
                "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
                "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
                "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
                "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
            };

            foreach (var state in states)
            {
                StateDropDown.Items.Add(new ListItem(state, state));
            }
        }

        private static void SelectListValue(DropDownList list, string value)
        {
            var item = list.Items.FindByValue(value ?? string.Empty);

            if (item != null)
            {
                list.ClearSelection();
                item.Selected = true;
            }
        }
    }
}
