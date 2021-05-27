Survey.StylesManager.applyTheme("modern");

window.survey = new Survey.Model(json);

survey.onComplete.add(function (result) {
  document.querySelector("#surveyResult").textContent =
    "Result JSON:\n" + JSON.stringify(result.data, null, 3);
});

survey.onUpdateQuestionCssClasses.add(function (survey, options) {
  var classes = options.cssClasses;

  classes.mainRoot += " sv_qstn";
  classes.root = "sq-root";
  classes.title += " sq-title";
  classes.item += " sq-item";
  classes.label += " sq-label";

  if (options.question.isRequired) {
    classes.title += " sq-title-required";
    classes.root += " sq-root-required";
  }

  // if (options.question.getType() === "checkbox") {
  //     classes.root += " sq-root-cb";
  // }
});

$("#surveyElement").Survey({ model: survey });
